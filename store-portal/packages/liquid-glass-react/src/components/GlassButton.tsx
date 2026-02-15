import * as React from 'react';
import { GlassSurface, type GlassSurfaceProps } from '../surface/GlassSurface';

export type GlassButtonProps = GlassSurfaceProps<'button'> & {
  type?: 'button' | 'submit' | 'reset';
};

export function GlassButton(props: GlassButtonProps) {
  const { type = 'button', preset = 'crystal', interactive = true, ...rest } = props;
  return (
    <GlassSurface
      as="button"
      preset={preset}
      interactive={interactive}
      type={type}
      {...rest}
    />
  );
}
