"use client";

import { useEffect, useRef, useCallback } from "react";
import createGlobe from "cobe";

interface GlobeProps {
  className?: string;
  dark?: boolean;
}

export function Globe({ className = "", dark = false }: GlobeProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointerInteracting = useRef<{ x: number; y: number } | null>(null);
  const dragOffset = useRef({ phi: 0, theta: 0 });
  const phiOffsetRef = useRef(0);
  const thetaOffsetRef = useRef(0);
  const isPausedRef = useRef(false);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    pointerInteracting.current = { x: e.clientX, y: e.clientY };
    if (canvasRef.current) canvasRef.current.style.cursor = "grabbing";
    isPausedRef.current = true;
  }, []);

  const handlePointerUp = useCallback(() => {
    if (pointerInteracting.current !== null) {
      phiOffsetRef.current += dragOffset.current.phi;
      thetaOffsetRef.current += dragOffset.current.theta;
      dragOffset.current = { phi: 0, theta: 0 };
    }
    pointerInteracting.current = null;
    if (canvasRef.current) canvasRef.current.style.cursor = "grab";
    isPausedRef.current = false;
  }, []);

  useEffect(() => {
    const handlePointerMove = (e: PointerEvent) => {
      if (pointerInteracting.current !== null) {
        dragOffset.current = {
          phi: (e.clientX - pointerInteracting.current.x) / 300,
          theta: (e.clientY - pointerInteracting.current.y) / 1000,
        };
      }
    };
    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    window.addEventListener("pointerup", handlePointerUp, { passive: true });
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [handlePointerUp]);

  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    let globe: ReturnType<typeof createGlobe> | null = null;
    let animationId: number;
    let phi = 0;

    // Indian corridor markers
    const markers = [
      { location: [12.97, 77.59] as [number, number], size: 0.04 },  // Bengaluru
      { location: [12.30, 76.65] as [number, number], size: 0.03 },  // Mysuru
      { location: [13.00, 77.76] as [number, number], size: 0.025 }, // Whitefield
      { location: [12.93, 77.62] as [number, number], size: 0.025 }, // Koramangala
      { location: [19.08, 72.88] as [number, number], size: 0.03 },  // Mumbai
      { location: [28.61, 77.21] as [number, number], size: 0.03 },  // Delhi
      { location: [17.39, 78.49] as [number, number], size: 0.025 }, // Hyderabad
    ];

    function init() {
      const width = canvas.offsetWidth;
      if (width === 0) return;
      if (globe) return;

      globe = createGlobe(canvas, {
        devicePixelRatio: Math.min(window.devicePixelRatio || 1, 2),
        width,
        height: width,
        phi: 1.4,       // Initial rotation to show India
        theta: 0.25,
        dark: dark ? 1 : 0,
        diffuse: dark ? 2.0 : 1.5,
        mapSamples: 20000,
        mapBrightness: dark ? 6 : 10,
        baseColor: dark ? [0.15, 0.15, 0.2] : [1, 1, 1],
        markerColor: dark ? [0.4, 0.7, 1.0] : [0.1, 0.2, 0.45],
        glowColor: dark ? [0.1, 0.1, 0.15] : [0.94, 0.93, 0.91],
        markers,
        opacity: dark ? 0.85 : 0.7,
      });

      function animate() {
        if (!isPausedRef.current) phi += 0.002;
        globe!.update({
          phi: phi + phiOffsetRef.current + dragOffset.current.phi,
          theta: 0.25 + thetaOffsetRef.current + dragOffset.current.theta,
        });
        animationId = requestAnimationFrame(animate);
      }
      animate();
      setTimeout(() => canvas && (canvas.style.opacity = "1"));
    }

    if (canvas.offsetWidth > 0) {
      init();
    } else {
      const ro = new ResizeObserver((entries) => {
        if (entries[0]?.contentRect.width > 0) {
          ro.disconnect();
          init();
        }
      });
      ro.observe(canvas);
    }

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
      if (globe) globe.destroy();
    };
  }, [dark]);

  return (
    <div className={`relative aspect-square select-none ${className}`}>
      <canvas
        ref={canvasRef}
        onPointerDown={handlePointerDown}
        style={{
          width: "100%",
          height: "100%",
          cursor: "grab",
          opacity: 0,
          transition: "opacity 1.2s ease",
          touchAction: "none",
        }}
      />
    </div>
  );
}
