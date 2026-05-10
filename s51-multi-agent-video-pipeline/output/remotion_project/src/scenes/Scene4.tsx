import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
} from "remotion";

interface SceneProps {
  frame: number;
  durationInFrames: number;
}

// Volcano particles
const VOLCANO_COUNT = 60;
const volcanoParticles = Array.from({ length: VOLCANO_COUNT }, (_, i) => ({
  id: i,
  offsetX: (Math.random() - 0.5) * 100,
  startY: Math.random() * 200 + 1600,
  size: 3 + Math.random() * 8,
  speed: 1 + Math.random() * 3,
  delay: Math.random() * 0.5,
  color: Math.random() > 0.5 ? "#FF4500" : "#FFD700",
}));

const LIGHTNING_COUNT = 4;

export const Scene4: React.FC<SceneProps> = ({ frame, durationInFrames }) => {
  const progress = frame / durationInFrames;

  // Lightning bolts (procedural) - generated inside component
  const lightningBolts = Array.from({ length: LIGHTNING_COUNT }, (_, i) => ({
    id: i,
    startX: 200 + Math.random() * 700,
    segments: 3 + Math.floor(Math.random() * 5),
    flashDuration: 3 + Math.random() * 5,
    flashDelay: Math.random() * durationInFrames,
  }));

  // Dolly in effect
  const dollyScale = interpolate(frame, [0, durationInFrames], [0.7, 1.1]);

  // Lightning flash
  const showLightning = lightningBolts.some((lb) => {
    const localFrame = (frame - lb.flashDelay + durationInFrames) % durationInFrames;
    return localFrame >= 0 && localFrame < lb.flashDuration;
  });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg, #1a0a00 0%, #2d1a0a 30%, #1a0f05 60%, #0a0500 100%)",
        transform: `scale(${dollyScale})`,
      }}
    >
      {/* Lightning flash overlay */}
      {showLightning && (
        <AbsoluteFill
          style={{
            backgroundColor: "rgba(255, 255, 255, 0.3)",
            zIndex: 5,
          }}
        />
      )}

      {/* Lightning bolts */}
      {lightningBolts.map((lb) => {
        const localFrame = (frame - lb.flashDelay + durationInFrames) % durationInFrames;
        if (localFrame <= 0 || localFrame > lb.flashDuration) return null;
        const intensity = interpolate(localFrame, [0, 1, lb.flashDuration - 1, lb.flashDuration], [1, 0.8, 0.6, 0]);
        return (
          <svg
            key={lb.id}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              zIndex: 4,
              opacity: intensity,
            }}
          >
            <polyline
              points={`${lb.startX},0 ${lb.startX - 30 + Math.random() * 60},${300 + Math.random() * 100} ${lb.startX + 20 - Math.random() * 40},${600 + Math.random() * 100} ${lb.startX - 40 + Math.random() * 80},${900 + Math.random() * 100}`}
              stroke="white"
              strokeWidth={3}
              fill="none"
              filter="url(#glow)"
            />
          </svg>
        );
      })}

      {/* Volcanic terrain (horizon) */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "60%",
          background: "linear-gradient(0deg, #1a0a00 0%, #3d1f0a 40%, #2d1505 70%, transparent 100%)",
          clipPath: "polygon(0% 100%, 5% 70%, 15% 80%, 25% 60%, 35% 75%, 45% 55%, 55% 70%, 65% 50%, 75% 65%, 85% 45%, 95% 60%, 100% 40%, 100% 100%)",
        }}
      />

      {/* Volcano glow */}
      <div
        style={{
          position: "absolute",
          bottom: "40%",
          left: "40%",
          width: 200,
          height: 200,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255, 69, 0, 0.4) 0%, transparent 70%)",
        }}
      />

      {/* Lava particles */}
      {volcanoParticles.map((p) => {
        const localProgress = Math.max(0, (frame / durationInFrames - p.delay) / (1 - p.delay));
        const y = p.startY - localProgress * 600 * p.speed;
        const x = 540 + p.offsetX + Math.sin(localProgress * 10) * 20;
        const opacity = interpolate(localProgress, [0, 0.3, 0.8, 1], [1, 0.8, 0.4, 0]);

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
              boxShadow: `0 0 ${p.size * 3}px ${p.color}`,
            }}
          />
        );
      })}

      {/* Primordial ocean glow */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "35%",
          background: "linear-gradient(0deg, rgba(0, 100, 150, 0.3) 0%, rgba(0, 50, 80, 0.1) 50%, transparent 100%)",
        }}
      />

      {/* Dialogo */}
      <div
        style={{
          position: "absolute",
          bottom: 140,
          left: 60,
          right: 60,
          color: "#ffcc99",
          fontFamily: "Georgia, serif",
          fontSize: 28,
          fontWeight: 600,
          textAlign: "center",
          textShadow: "0 2px 20px rgba(255, 50, 0, 0.5)",
          lineHeight: 1.4,
          zIndex: 10,
          opacity: interpolate(frame, [30, 70, durationInFrames - 20, durationInFrames], [0, 1, 1, 0]),
        }}
      >
        "En la Tierra, el caos químico dio paso al milagro. Moléculas simples se
        combinaron para crear vida. Primeras células, primeros océanos llenos
        de posibilidades. La vida encontró su camino."
      </div>
    </AbsoluteFill>
  );
};
