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

// Planet configs for orbital motion
const planets = [
  { name: "Mercury", size: 15, orbitRadius: 100, color: "#A0522D", speed: 2.5, angle: 0 },
  { name: "Venus", size: 25, orbitRadius: 170, color: "#DEB887", speed: 1.8, angle: 1.2 },
  { name: "Earth", size: 28, orbitRadius: 250, color: "#4169E1", speed: 1.5, angle: 2.8 },
  { name: "Mars", size: 20, orbitRadius: 330, color: "#CD5C5C", speed: 1.2, angle: 4.1 },
  { name: "Jupiter", size: 50, orbitRadius: 430, color: "#DAA520", speed: 0.8, angle: 5.5 },
  { name: "Saturn", size: 42, orbitRadius: 530, color: "#F4A460", speed: 0.6, angle: 0.7 },
];

export const Scene3: React.FC<SceneProps> = ({ frame, durationInFrames }) => {
  const { fps } = useVideoConfig();
  const progress = frame / durationInFrames;

  // Sun pulse
  const sunPulse = Math.sin(frame * 0.1) * 0.1 + 1;

  // Orbital rotation
  const orbitRotation = spring({
    frame,
    fps,
    config: { damping: 20, stiffness: 40 },
  });

  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(ellipse at center, #1a0a2e 0%, #0a0015 50%, #000005 100%)",
      }}
    >
      {/* Sun */}
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: 120 * sunPulse,
            height: 120 * sunPulse,
            borderRadius: "50%",
            background: "radial-gradient(circle, #FFD700 0%, #FFA500 30%, #FF4500 60%, transparent 100%)",
            boxShadow: "0 0 80px #FFA500, 0 0 160px #FF450066",
            opacity: interpolate(frame, [0, 15], [0, 1]),
          }}
        />
      </AbsoluteFill>

      {/* Orbital rings */}
      {planets.map((p, idx) => (
        <React.Fragment key={p.name}>
          {/* Orbit path */}
          <AbsoluteFill
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                width: p.orbitRadius * 2,
                height: p.orbitRadius * 2,
                borderRadius: "50%",
                border: "1px solid rgba(255,255,255,0.08)",
                position: "absolute",
              }}
            />
          </AbsoluteFill>

          {/* Planet */}
          <AbsoluteFill
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                position: "absolute",
                width: 0,
                height: 0,
                transform: `rotate(${frame * p.speed + p.angle * 40}deg)`,
              }}
            >
              <div
                style={{
                  position: "absolute",
                  left: p.orbitRadius - p.size / 2,
                  top: -p.size / 2,
                  width: p.size,
                  height: p.size,
                  borderRadius: "50%",
                  backgroundColor: p.color,
                  boxShadow: `0 0 ${p.size / 2}px ${p.color}66`,
                  opacity: interpolate(frame, [10 + idx * 5, 30 + idx * 5], [0, 1]),
                }}
              />
              {/* Saturn rings */}
              {p.name === "Saturn" && (
                <div
                  style={{
                    position: "absolute",
                    left: p.orbitRadius - p.size * 1.2,
                    top: -p.size * 0.3,
                    width: p.size * 2.4,
                    height: p.size * 0.4,
                    borderRadius: "50%",
                    border: "3px solid rgba(210, 180, 140, 0.5)",
                    transform: "rotate(-20deg)",
                    opacity: 0.6,
                  }}
                />
              )}
            </div>
          </AbsoluteFill>
        </React.Fragment>
      ))}

      {/* Dialogo */}
      <div
        style={{
          position: "absolute",
          bottom: 140,
          left: 60,
          right: 60,
          color: "#FFE4B5",
          fontFamily: "Georgia, serif",
          fontSize: 30,
          fontWeight: 600,
          textAlign: "center",
          textShadow: "0 2px 20px rgba(255, 100, 0, 0.6)",
          lineHeight: 1.4,
          zIndex: 10,
          opacity: interpolate(frame, [20, 50, durationInFrames - 15, durationInFrames], [0, 1, 1, 0]),
        }}
      >
        "En un brazo de una galaxia ordinaria, una estrella llamada Sol encendió
        su fuego. A su alrededor, planetas de roca y gas comenzaron a danzar:
        nuestro sistema solar."
      </div>
    </AbsoluteFill>
  );
};
