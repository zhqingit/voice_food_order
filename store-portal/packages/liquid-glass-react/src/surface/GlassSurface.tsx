import * as React from 'react';

type GlassPreset = 'subtle' | 'frosted' | 'crystal' | 'vibrant' | 'contrast';

type PolymorphicProps<E extends React.ElementType> = {
  as?: E;
} & Omit<React.ComponentPropsWithoutRef<E>, 'as' | 'color'>;

export type GlassSurfaceProps<E extends React.ElementType = 'div'> = PolymorphicProps<E> & {
  preset?: GlassPreset;
  interactive?: boolean;
  radius?: number | string;
};

function usePrefersReducedMotion() {
  const [reduced, setReduced] = React.useState(false);

  React.useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => setReduced(Boolean(media.matches));
    onChange();
    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', onChange);
      return () => media.removeEventListener('change', onChange);
    }
    media.addListener(onChange);
    return () => media.removeListener(onChange);
  }, []);

  return reduced;
}

export function GlassSurface<E extends React.ElementType = 'div'>(
  props: GlassSurfaceProps<E>
) {
  const {
    as,
    preset = 'frosted',
    interactive = false,
    radius,
    className,
    style,
    ...rest
  } = props;

  const Component = (as ?? 'div') as React.ElementType;

  const prefersReducedMotion = usePrefersReducedMotion();
  const shouldBeInteractive = interactive && !prefersReducedMotion;
  const elementRef = React.useRef<HTMLElement | null>(null);
  const rafIdRef = React.useRef<number | null>(null);
  const lastPointRef = React.useRef<{ clientX: number; clientY: number } | null>(null);

  const scheduleUpdate = React.useCallback(() => {
    if (rafIdRef.current !== null) return;
    rafIdRef.current = window.requestAnimationFrame(() => {
      rafIdRef.current = null;
      const el = elementRef.current;
      const pt = lastPointRef.current;
      if (!el || !pt) return;
      const rect = el.getBoundingClientRect();
      const x = pt.clientX - rect.left;
      const y = pt.clientY - rect.top;
      el.style.setProperty('--glass-px', `${x}px`);
      el.style.setProperty('--glass-py', `${y}px`);
      el.style.setProperty('--glass-active', '1');
    });
  }, []);

  React.useEffect(() => {
    return () => {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
    };
  }, []);

  const onPointerMove = React.useCallback(
    (e: React.PointerEvent) => {
      if (!shouldBeInteractive) return;
      lastPointRef.current = { clientX: e.clientX, clientY: e.clientY };
      scheduleUpdate();
    },
    [scheduleUpdate, shouldBeInteractive]
  );

  const onPointerEnter = React.useCallback(
    (e: React.PointerEvent) => {
      if (!shouldBeInteractive) return;
      lastPointRef.current = { clientX: e.clientX, clientY: e.clientY };
      scheduleUpdate();
    },
    [scheduleUpdate, shouldBeInteractive]
  );

  const onPointerLeave = React.useCallback(() => {
    const el = elementRef.current;
    if (!el) return;
    el.style.setProperty('--glass-active', '0');
  }, []);

  const onFocus = React.useCallback(() => {
    const el = elementRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty('--glass-px', `${rect.width / 2}px`);
    el.style.setProperty('--glass-py', `${rect.height / 2}px`);
    el.style.setProperty('--glass-active', '1');
  }, []);

  const onBlur = React.useCallback(() => {
    const el = elementRef.current;
    if (!el) return;
    el.style.setProperty('--glass-active', '0');
  }, []);

  return (
    <Component
      ref={(node: HTMLElement | null) => {
        elementRef.current = node;
      }}
      data-glass=""
      data-glass-preset={preset}
      data-glass-interactive={shouldBeInteractive ? '' : undefined}
      className={className}
      style={{
        ...style,
        ...(radius !== undefined ? { ['--glass-radius' as any]: typeof radius === 'number' ? `${radius}px` : radius } : null)
      }}
      onPointerEnter={(e: React.PointerEvent) => {
        (rest as any).onPointerEnter?.(e);
        onPointerEnter(e);
      }}
      onPointerMove={(e: React.PointerEvent) => {
        (rest as any).onPointerMove?.(e);
        onPointerMove(e);
      }}
      onPointerLeave={(e: React.PointerEvent) => {
        (rest as any).onPointerLeave?.(e);
        onPointerLeave();
      }}
      onFocus={(e: React.FocusEvent) => {
        (rest as any).onFocus?.(e);
        onFocus();
      }}
      onBlur={(e: React.FocusEvent) => {
        (rest as any).onBlur?.(e);
        onBlur();
      }}
      {...rest}
    />
  );
}
