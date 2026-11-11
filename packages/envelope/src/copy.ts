// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The copy of a forwarded envelope into the one stamped for this hop (U3
// NP-07; NFR-AE-19). In-house and iterative, never structuredClone, whose
// depth behaviour is the engine's.
//
// Every key is created as an own data property (Object.defineProperty:
// enumerable, writable, configurable), so a key named __proto__, as JSON.parse
// produces it, is copied as a field and never sets a prototype. Every copied
// object has Object.prototype as its prototype.

type Container = Record<string, unknown> | unknown[];

function isContainer(value: unknown): value is Container {
  return typeof value === 'object' && value !== null;
}

function empty(like: Container): Container {
  return Array.isArray(like) ? [] : {};
}

function put(target: Container, key: string, value: unknown): void {
  Object.defineProperty(target, key, {
    value,
    enumerable: true,
    writable: true,
    configurable: true,
  });
}

/** A deep copy of a JSON value, without recursion. */
export function copyJson<T>(value: T): T {
  if (!isContainer(value)) return value;
  const root = empty(value);
  const pending: [Container, Container][] = [[value, root]];
  while (pending.length > 0) {
    const [source, target] = pending.pop()!;
    if (Array.isArray(source)) {
      const out = target as unknown[];
      for (const item of source) {
        if (isContainer(item)) {
          const child = empty(item);
          out.push(child);
          pending.push([item, child]);
        } else out.push(item);
      }
    } else {
      for (const key of Object.keys(source)) {
        const item = source[key];
        if (isContainer(item)) {
          const child = empty(item);
          put(target, key, child);
          pending.push([item, child]);
        } else put(target, key, item);
      }
    }
  }
  return root as T;
}
