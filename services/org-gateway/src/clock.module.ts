// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Provides the clock and the lifetimes from @soorma/org-identity.
import { Module } from '@nestjs/common';
import { CLOCK, Lifetimes, systemClock } from '@soorma/org-identity';

@Module({
  providers: [{ provide: CLOCK, useValue: systemClock }, Lifetimes],
  exports: [CLOCK, Lifetimes],
})
export class ClockModule {}
