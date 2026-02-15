import * as React from 'react';
import { GlassSurface, type GlassSurfaceProps } from '../surface/GlassSurface';

export type GlassPanelProps = GlassSurfaceProps<'section'>;

export function GlassPanel(props: GlassPanelProps) {
  return <GlassSurface as="section" preset="subtle" {...props} />;
}
