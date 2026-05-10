import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface SceneProps {
  frame: number;
  durationInFrames: number;
}

// Earth pixels (simplified)
const EARTH_PIXELS = 600;
const earthPixels = Array.from({ length: EARTH_PIXELS }, (_, i) => ({
  id: i,
  angle: Math.random() * Math.PI * 2,
  radius: 20 + Math.random() * 180,
  color: Math.random() > 0.6
    ? `hsl(${200 + Math.random() * 30}, 70%, ${40 + Math.random() * 20}%)`
    : `hsl(${120 + Math.random() * 40}, 50%, ${30 + Math.random() * 20}%)`,
  size: 2 + Math.random() * 4,
}));

// Star field
const STAR_COUNT = 400;
const stars = Array.from({ length: STAR_COUNT }, (_, i) => ({
  id: i,
  x: Math.random() * 1080,
  y: Math.random() * 1920,
  size: 0.5 + Math.random() * 2,
  brightness: 0.2 + Math.random() * 0.8,
}));

export const Scene6: React.FC<SceneProps> = ({ frame, durationInFrames }) => {
  const { fps } = useVideoConfig();
  const progress = frame / durationInFrames;

  // Crane up: camera pulls up and away
  const craneOffset = interpolate(frame, [0, durationInFrames], [0, -300]);
  const earthScale = interpolate(frame, [0, durationInFrames], [1, 0.3]);

  // Earth rotation
  const earthRotation = frame * 0.5;

  // Warm light pulse (hope)
  const warmPulse = Math.sin(frame * 0.05) * 0.15 + 1;

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg, #050510 0%, #0a0a2e 30%, #050510 100%)",
        transform: `translateY(${craneOffset}px)`,
      }}
    >
      {/* Star field */}
      {stars.map((s) => (
        <div
          key={s.id}
          style={{
            position: "absolute",
            left: s.x,
            top: s.y,
            width: s.size,
            height: s.size,
            borderRadius: "50%",
            backgroundColor: `rgba(255, 255, 255, ${s.brightness})`,
          }}
        />
      ))}

      {/* Milky Way glow */}
      <div
        style={{
          position: "absolute",
          left: "10%",
          top: "20%",
          width: "80%",
          height: "40%",
          background: "linear-gradient(90deg, transparent, rgba(100, 50, 150, 0.1) 30%, rgba(150, 100, 200, 0.15) 50%, rgba(100, 50, 150, 0.1) 70%, transparent)",
          borderRadius: "50%",
          filter: "blur(40px)",
          transform: "rotate(-15deg)",
        }}
      />

      {/* Earth */}
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: 400 * earthScale,
            height: 400 * earthScale,
            borderRadius: "50%",
            background: `radial-gradient(circle at 35% 40%, #4A90D9 0%, #2E6DB4 30%, #1A4A7A 60%, #0D2B4E 100%)`,
            boxShadow: `
              0 0 ${60 * warmPulse}px rgba(100, 200, 255, 0.3),
              inset -30px -20px 50px rgba(0,0,0,0.5)
            `,
            transform: `rotate(${earthRotation}deg)`,
            opacity: interpolate(frame, [0, 20], [0, 1]),
            overflow: "hidden",
          }}
        >
          {/* Land masses (simplified blobs) */}
          <div style={{
            position: "absolute",
            top: "30%",
            left: "20%",
            width: "25%",
            height: "20%",
            background: "#3A7A3A",
            borderRadius: "60% 40% 50% 30%",
            opacity: 0.7,
          }} />
          <div style={{
            position: "absolute",
            top: "20%",
            left: "55%",
            width: "20%",
            height: "25%",
            background: "#4A8A3A",
            borderRadius: "40% 50% 30% 60%",
            opacity: 0.6,
          }} />
          <div style={{
            position: "absolute",
            top: "50%",
            left: "45%",
            width: "15%",
            height: "20%",
            background: "#3A7A3A",
            borderRadius: "50% 30% 40% 60%",
            opacity: 0.5,
          }} />

          {/* Atmosphere glow */}
          <div style={{
            position: "absolute",
            top: -10,
            left: -10,
            width: "105%",
            height: "105%",
            borderRadius: "50%",
            boxShadow: "inset 0 0 40px rgba(100, 180, 255, 0.2)",
          }} />
        </div>
      </AbsoluteFill>

      {/* Warm light rays (hope) */}
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: interpolate(frame, [60, durationInFrames], [0, 0.3]),
        }}
      >
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              width: 2,
              height: 800 * warmPulse,
              background: `linear-gradient(180deg, rgba(255, 200, 100, 0.1), transparent)`,
              transform: `rotate(${i * 30}deg)`,
              transformOrigin: "center bottom",
              bottom: "50%",
            }}
          />
        ))}
      </AbsoluteFill>

      {/* Dialogo */}
      <div
        style={{
          position: "absolute",
          bottom: 140,
          left: 60,
          right: 60,
          color: "#c8d8ff",
          fontFamily: "Georgia, serif",
          fontSize: 28,
          fontWeight: 600,
          textAlign: "center",
          textShadow: "0 2px 30px rgba(50, 100, 255, 0.5)",
          lineHeight: 1.4,
          zIndex: 10,
          opacity: interpolate(frame, [30, 70, durationInFrames - 30, durationInFrames], [0, 1, 1, 0]),
        }}
      >
        "Somos polvo de estrellas. El universo no solo creó galaxias y planetas...
        también creó ojos para contemplarse a sí mismo. Y el viaje continúa."
      </div>
    </AbsoluteFill>
  );
};
