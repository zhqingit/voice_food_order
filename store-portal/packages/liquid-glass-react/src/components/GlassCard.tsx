import * as React from 'react';
import { GlassSurface, type GlassSurfaceProps } from '../surface/GlassSurface';

export type GlassCardProps = GlassSurfaceProps<'div'>;

export function GlassCard(props: GlassCardProps) {
  return <GlassSurface preset="frosted" {...props} />;
}
