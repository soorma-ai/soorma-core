// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The Compose healthcheck's entry point (D-ID-OI-05). The check itself is
// @soorma/service-kit's (U4 NP-EHA-15); this file keeps dist/healthcheck.js in
// S1's image, so compose.yaml is unchanged (D-CG-EHA-13).
import { runHealthcheck } from '@soorma/service-kit';

runHealthcheck();
