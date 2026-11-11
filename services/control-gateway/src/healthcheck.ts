// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The Compose healthcheck's entry point: @soorma/service-kit's check, as S1's
// (D-CG-EHA-13), so the image has dist/healthcheck.js.
import { runHealthcheck } from '@soorma/service-kit';

runHealthcheck();
