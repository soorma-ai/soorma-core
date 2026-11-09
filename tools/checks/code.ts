// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Code checks over the TypeScript of every package, seam, and service source
// (src/ only), through the TypeScript compiler API and its type checker:
//
//   sql      (D-CG-OI-04; NFR-OI-17) every `.query(` call takes a Statement as
//            its first argument; statement() and migrationStatement() are
//            called only in a package's src/sql.ts (migrationStatement also
//            in the migration runner); a sql.ts has no template literal with
//            a substitution
//   compare  (D-CG-OI-05; NFR-OI-29) no `===` or `!==` where either operand's
//            type is, or is a union containing, a branded secret type
//            (SecretBytes, Verifier, SecretText, TotpCode). Names play no part
//   inject   (D-CG-OI-03; T-OI-08) every constructor parameter of a class the
//            injector builds (@Injectable or @Controller) has an @Inject(TOKEN)
import { readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import ts from 'typescript';
import { repoRoot, type Finding } from './workspace.ts';

/** The TypeScript projects whose src/ the checks read: each package's own tsconfig.json. */
export function sourceProjects(root: string = repoRoot): string[] {
  const out: string[] = [];
  for (const base of ['packages', 'seams', 'services']) {
    let names: string[];
    try {
      names = readdirSync(join(root, base));
    } catch {
      continue;
    }
    for (const name of names.sort()) {
      const config = join(root, base, name, 'tsconfig.json');
      try {
        if (statSync(config).isFile()) out.push(config);
      } catch {
        // not a package
      }
    }
  }
  return out;
}

export interface CheckedProgram {
  program: ts.Program;
  /** The source files checked: those under a src/ directory. */
  files: ts.SourceFile[];
  root: string;
}

export function programFor(configPath: string, root: string = repoRoot): CheckedProgram {
  const parsed = ts.getParsedCommandLineOfConfigFile(
    configPath,
    {},
    {
      ...ts.sys,
      onUnRecoverableConfigFileDiagnostic: () => undefined,
    },
  );
  if (!parsed) throw new Error(`cannot read ${configPath}`);
  const program = ts.createProgram(parsed.fileNames, parsed.options);
  const dir = configPath.slice(0, -'tsconfig.json'.length);
  const files = program
    .getSourceFiles()
    .filter((f) => f.fileName.startsWith(join(dir, 'src')) && !f.isDeclarationFile);
  return { program, files, root };
}

function at(checked: CheckedProgram, file: ts.SourceFile, node: ts.Node): string {
  const { line } = file.getLineAndCharacterOfPosition(node.getStart(file));
  return `${relative(checked.root, file.fileName)}:${line + 1}`;
}

function visit(node: ts.Node, fn: (n: ts.Node) => void): void {
  fn(node);
  ts.forEachChild(node, (child) => visit(child, fn));
}

/** True when the type, or any member of a union, carries a property whose name contains `brand`. */
function hasBrand(checker: ts.TypeChecker, type: ts.Type, brands: readonly string[]): boolean {
  const types = type.isUnion() ? type.types : [type];
  return types.some((t) =>
    checker
      .getPropertiesOfType(t)
      .some((p) => brands.some((b) => String(p.escapedName).includes(b))),
  );
}

const STATEMENT_BRAND = ['statementBrand'];
export const SECRET_BRANDS = [
  'secretBytesBrand',
  'verifierBrand',
  'secretTextBrand',
  'totpCodeBrand',
] as const;

const isSqlModule = (file: ts.SourceFile): boolean => /[\\/]src[\\/]sql\.ts$/.test(file.fileName);
const isMigrationRunner = (file: ts.SourceFile): boolean =>
  /[\\/]src[\\/]store[\\/]migrations\.ts$/.test(file.fileName);

export function sqlFindings(checked: CheckedProgram): Finding[] {
  const checker = checked.program.getTypeChecker();
  const findings: Finding[] = [];
  const add = (file: ts.SourceFile, node: ts.Node, message: string): void => {
    findings.push({ check: 'sql', location: at(checked, file, node), message });
  };
  for (const file of checked.files) {
    visit(file, (node) => {
      if (ts.isCallExpression(node)) {
        const callee = node.expression;
        const name = ts.isPropertyAccessExpression(callee)
          ? callee.name.text
          : ts.isIdentifier(callee)
            ? callee.text
            : undefined;
        if (name === 'query' && ts.isPropertyAccessExpression(callee)) {
          const first = node.arguments[0];
          if (!first || !hasBrand(checker, checker.getTypeAtLocation(first), STATEMENT_BRAND))
            add(file, node, 'query() takes a statement from a src/sql.ts, never other SQL');
        }
        if (name === 'statement' && !isSqlModule(file))
          add(file, node, 'statement() is called only in a package’s src/sql.ts');
        if (name === 'migrationStatement' && !isSqlModule(file) && !isMigrationRunner(file))
          add(file, node, 'migrationStatement() is for the migration runner only');
      }
      if (isSqlModule(file) && ts.isTemplateExpression(node))
        add(file, node, 'a template literal with a substitution in sql.ts');
    });
  }
  return findings;
}

export function compareFindings(checked: CheckedProgram): Finding[] {
  const checker = checked.program.getTypeChecker();
  const findings: Finding[] = [];
  for (const file of checked.files) {
    visit(file, (node) => {
      if (!ts.isBinaryExpression(node)) return;
      const op = node.operatorToken.kind;
      if (
        op !== ts.SyntaxKind.EqualsEqualsEqualsToken &&
        op !== ts.SyntaxKind.ExclamationEqualsEqualsToken
      )
        return;
      const secret = [node.left, node.right].some((side) =>
        hasBrand(checker, checker.getTypeAtLocation(side), SECRET_BRANDS),
      );
      if (secret)
        findings.push({
          check: 'compare',
          location: at(checked, file, node),
          message: 'a secret value compared with === or !==; use secretEqual',
        });
    });
  }
  return findings;
}

const INJECTED = new Set(['Injectable', 'Controller']);

function decoratorName(decorator: ts.Decorator): string | undefined {
  const e = decorator.expression;
  if (ts.isCallExpression(e) && ts.isIdentifier(e.expression)) return e.expression.text;
  if (ts.isIdentifier(e)) return e.text;
  return undefined;
}

export function injectFindings(checked: CheckedProgram): Finding[] {
  const findings: Finding[] = [];
  for (const file of checked.files) {
    visit(file, (node) => {
      if (!ts.isClassDeclaration(node)) return;
      const decorators = ts.getDecorators(node) ?? [];
      if (!decorators.some((d) => INJECTED.has(decoratorName(d) ?? ''))) return;
      const ctor = node.members.find(ts.isConstructorDeclaration);
      for (const parameter of ctor?.parameters ?? []) {
        const injected = (ts.getDecorators(parameter) ?? []).some(
          (d) => decoratorName(d) === 'Inject',
        );
        if (!injected)
          findings.push({
            check: 'inject',
            location: at(checked, file, parameter),
            message: `constructor parameter of ${node.name?.text ?? 'a class'} has no @Inject(TOKEN)`,
          });
      }
    });
  }
  return findings;
}

/** Each check over every source project. */
export function codeFindings(
  check: 'sql' | 'compare' | 'inject',
  root: string = repoRoot,
): Finding[] {
  const fn = { sql: sqlFindings, compare: compareFindings, inject: injectFindings }[check];
  return sourceProjects(root).flatMap((config) => fn(programFor(config, root)));
}
