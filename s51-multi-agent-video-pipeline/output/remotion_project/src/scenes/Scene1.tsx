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

// Helper: generate random particles
const PARTICLE_COUNT = 80;
const particles = Array.from({ length: PARTICLE_COUNT }, (_, i) => ({
  id: i,
  angle: Math.random() * Math.PI * 2,
  speed: 0.3 + Math.random() * 0.7,
  size: 2 + Math.random() * 6,
  color: i % 3 === 0 ? "#FF6B35" : i % 3 === 1 ? "#00BFFF" : "#FFFFFF",
  delay: Math.random() * 0.3,
}));

export const Scene1: React.FC<SceneProps> = ({ frame, durationInFrames }) => {
  const { fps } = useVideoConfig();
  const progress = frame / durationInFrames;

  // Big Bang flash intensity
  const flashIntensity = interpolate(frame, [0, 5, 15], [1, 0.8, 0], {
    extrapolateRight: "clamp",
  });

  // Camera shake (simulated with transform)
  const shakeX = spring({
    frame,
    fps,
    config: { damping: 4, stiffness: 200 },
  });
  const shakeOffsetX = interpolate(shakeX, [0, 1], [0, 15]);

  // Zoom out effect
  const zoomScale = interpolate(frame, [0, durationInFrames], [0.5, 1.5]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#000",
        transform: `scale(${zoomScale}) translateX(${shakeOffsetX}px)`,
      }}
    >
      {/* Flash overlay */}
      <AbsoluteFill
        style={{
          backgroundColor: `rgba(255, 255, 255, ${flashIntensity * 0.6})`,
          zIndex: 5,
        }}
      />

      {/* Core explosion center */}
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: interpolate(frame, [0, 30, 60], [50, 200, 400]),
            height: interpolate(frame, [0, 30, 60], [50, 200, 400]),
            borderRadius: "50%",
            background: `radial-gradient(circle, 
              rgba(255,255,255,${interpolate(frame, [0, 15, 60], [1, 0.8, 0.3])}) 0%,
              rgba(0,191,255,${interpolate(frame, [0, 20, 60], [0.8, 0.5, 0.1])}) 30%,
              rgba(255,107,53,${interpolate(frame, [0, 25, 60], [0.6, 0.3, 0])}) 60%,
              transparent 100%
            )`,
            opacity: interpolate(frame, [0, 60, durationInFrames], [1, 0.8, 0.4]),
          }}
        />
      </AbsoluteFill>

      {/* Expanding ring */}
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: interpolate(frame, [10, durationInFrames], [100, 2000]),
            height: interpolate(frame, [10, durationInFrames], [100, 2000]),
            borderRadius: "50%",
            border: `2px solid rgba(255, 255, 255, ${interpolate(frame, [10, 60, durationInFrames], [0.8, 0.3, 0])})`,
            opacity: interpolate(frame, [10, 60, durationInFrames], [0.8, 0.3, 0]),
          }}
        />
      </AbsoluteFill>

      {/* Particles */}
      {particles.map((p) => {
        const particleProgress = Math.max(
          0,
          (frame / durationInFrames - p.delay) / (1 - p.delay)
        );
        const radius = particleProgress * 800 * p.speed;
        const x = Math.cos(p.angle) * radius + 540;
        const y = Math.sin(p.angle) * radius + 960;
        const opacity = interpolate(
          particleProgress,
          [0, 0.1, 0.7, 1],
          [0, 1, 0.8, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
        );

        return (
          <div
            key={p.id}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: p.size,
              height: p.size,
              borderRadius: "50%",
              backgroundColor: p.color,
              opacity,
              boxShadow: `0 0 ${p.size * 2}px ${p.color}`,
            }}
          />
        );
      })}

      {/* Dialogo */}
      <div
        style={{
          position: "absolute",
          bottom: 140,
          left: 60,
          right: 60,
          color: "white",
          fontFamily: "Georgia, serif",
          fontSize: 32,
          fontWeight: 600,
          textAlign: "center",
          textShadow: "0 2px 20px rgba(0,0,0,0.9)",
          lineHeight: 1.4,
          zIndex: 10,
          opacity: interpolate(frame, [20, 40, durationInFrames - 10, durationInFrames], [0, 1, 1, 0]),
        }}
      >
        "Al principio, todo era un punto infinitamente pequeño y denso.
        Hace 13.8 mil millones de años... ese punto explotó. Nació el universo."
      </div>
    </AbsoluteFill>
  );
};
