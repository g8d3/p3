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

// Generate nebula particles
const NEBULA_COUNT = 120;
const nebulaParticles = Array.from({ length: NEBULA_COUNT }, (_, i) => ({
  id: i,
  x: Math.random() * 1080,
  y: Math.random() * 1920,
  size: 3 + Math.random() * 12,
  color: Math.random() > 0.5
    ? `rgba(128, 0, 255, ${0.1 + Math.random() * 0.3})`
    : `rgba(255, 165, 0, ${0.1 + Math.random() * 0.3})`,
  speedX: (Math.random() - 0.5) * 0.3,
  speedY: (Math.random() - 0.5) * 0.3,
}));

// Generate stars
const STAR_COUNT = 300;
const stars = Array.from({ length: STAR_COUNT }, (_, i) => ({
  id: i,
  x: Math.random() * 1080,
  y: Math.random() * 1920,
  size: 0.5 + Math.random() * 2,
  brightness: 0.3 + Math.random() * 0.7,
  twinkleSpeed: 0.5 + Math.random() * 2,
}));

// Galaxies
const GALAXY_COUNT = 5;
const galaxies = Array.from({ length: GALAXY_COUNT }, (_, i) => ({
  id: i,
  x: 200 + Math.random() * 700,
  y: 300 + Math.random() * 1300,
  size: 60 + Math.random() * 100,
  rotation: Math.random() * 360,
  color: i % 2 === 0 ? "#9B59B6" : "#E67E22",
  opacity: 0.3 + Math.random() * 0.4,
}));

export const Scene2: React.FC<SceneProps> = ({ frame, durationInFrames }) => {
  const progress = frame / durationInFrames;

  // Fly-through parallax
  const parallaxOffset = interpolate(frame, [0, durationInFrames], [0, 200]);

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg, #0D0015 0%, #1A0030 40%, #0D0820 70%, #050510 100%)",
      }}
    >
      {/* Nebula clouds */}
      {nebulaParticles.map((p) => {
        const x = (p.x + p.speedX * frame * 2 + 1080) % 1080;
        const y = (p.y + p.speedY * frame + parallaxOffset + 1920) % 1920;
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
              background: p.color,
              filter: "blur(4px)",
            }}
          />
        );
      })}

      {/* Stars */}
      {stars.map((s) => {
        const twinkle = Math.sin(frame * s.twinkleSpeed * 0.05) * 0.3 + 0.7;
        return (
          <div
            key={s.id}
            style={{
              position: "absolute",
              left: s.x,
              top: (s.y + parallaxOffset * 0.3) % 1920,
              width: s.size,
              height: s.size,
              borderRadius: "50%",
              backgroundColor: `rgba(255, 255, 255, ${s.brightness * twinkle})`,
            }}
          />
        );
      })}

      {/* Galaxies */}
      {galaxies.map((g) => {
        const rotation = g.rotation + frame * 0.2;
        const opacity = g.opacity * interpolate(
          Math.sin(frame * 0.1 + g.id),
          [-1, 1],
          [0.5, 1]
        );
        return (
          <div
            key={g.id}
            style={{
              position: "absolute",
              left: g.x - g.size / 2,
              top: (g.y + parallaxOffset * 0.5) % 1920 - g.size / 2,
              width: g.size,
              height: g.size,
              borderRadius: "50%",
              background: `radial-gradient(ellipse, ${g.color}66 0%, ${g.color}22 40%, transparent 70%)`,
              transform: `rotate(${rotation}deg)`,
              opacity,
              filter: "blur(2px)",
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
          color: "#e8d5ff",
          fontFamily: "Georgia, serif",
          fontSize: 30,
          fontWeight: 600,
          textAlign: "center",
          textShadow: "0 2px 30px rgba(100, 0, 200, 0.8)",
          lineHeight: 1.4,
          zIndex: 10,
          opacity: interpolate(frame, [30, 60, durationInFrames - 20, durationInFrames], [0, 1, 1, 0]),
        }}
      >
        "El universo se expandió y enfrió. La gravedad unió el gas y el polvo
        cósmico, encendiendo miles de millones de estrellas. Nacieron las
        galaxias: inmensas islas de luz en la oscuridad infinita."
      </div>
    </AbsoluteFill>
  );
};
