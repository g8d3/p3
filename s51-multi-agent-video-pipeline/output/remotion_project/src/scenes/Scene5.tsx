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

// Evolution stages with their visual representations
const evolutionStages = [
  { label: "Célula", emoji: "🦠", time: 0, color: "#00FF88" },
  { label: "Pez", emoji: "🐟", time: 0.15, color: "#00BFFF" },
  { label: "Anfibio", emoji: "🦎", time: 0.3, color: "#32CD32" },
  { label: "Dinosaurio", emoji: "🦕", time: 0.45, color: "#8B4513" },
  { label: "Primate", emoji: "🦧", time: 0.6, color: "#D2691E" },
  { label: "Humano", emoji: "🧑", time: 0.75, color: "#FFD700" },
  { label: "Civilización", emoji: "🚀", time: 0.9, color: "#FF4500" },
];

// Civilization flash images
const civFlashes = [
  { emoji: "🔥", label: "Fuego", time: 0.78 },
  { emoji: "☸️", label: "Rueda", time: 0.84 },
  { emoji: "💡", label: "Electricidad", time: 0.9 },
  { emoji: "🚀", label: "Espacio", time: 0.96 },
];

export const Scene5: React.FC<SceneProps> = ({ frame, durationInFrames }) => {
  const { fps } = useVideoConfig();
  const progress = frame / durationInFrames;

  // Fast dolly out
  const dollyScale = interpolate(frame, [0, durationInFrames], [0.3, 1.5], {
    extrapolateRight: "clamp",
  });

  // Speed lines intensity
  const speedLines = interpolate(frame, [0, 30, durationInFrames - 20, durationInFrames], [0, 0.6, 0.8, 0]);

  // Current stage
  const currentStage = evolutionStages
    .filter((s) => progress >= s.time)
    .pop() || evolutionStages[0];

  const nextStage = evolutionStages.find((s) => s.time > progress) || evolutionStages[evolutionStages.length - 1];
  const transitionBetween = nextStage.time - (evolutionStages.find((s) => s.time === currentStage.time)?.time || 0);
  const stageProgress = transitionBetween > 0
    ? (progress - currentStage.time) / transitionBetween
    : 0;

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at center, ${currentStage.color}22 0%, #000000 70%)`,
        transform: `scale(${dollyScale})`,
      }}
    >
      {/* Speed lines */}
      {Array.from({ length: 20 }).map((_, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
            width: 2,
            height: 60 + Math.random() * 120,
            background: `linear-gradient(180deg, transparent, rgba(255,255,255,${speedLines * (0.2 + Math.random() * 0.3)}), transparent)`,
            opacity: speedLines,
            transform: `rotate(${-5 + Math.random() * 10}deg)`,
          }}
        />
      ))}

      {/* Main evolution stage display */}
      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 30,
        }}
      >
        {/* Emoji/icon */}
        <div
          style={{
            fontSize: interpolate(
              Math.min(stageProgress, 0.5) * 2,
              [0, 1],
              [120, 200]
            ),
            opacity: interpolate(stageProgress, [0, 0.3, 0.7, 1], [0, 1, 1, 0]),
            transform: `scale(${interpolate(stageProgress, [0, 0.2, 0.8, 1], [0.5, 1, 1, 0.5])})`,
            filter: `brightness(${interpolate(stageProgress, [0, 0.2, 0.8, 1], [0.3, 1, 1, 0.3])})`,
          }}
        >
          {currentStage.emoji}
        </div>

        {/* Label */}
        <div
          style={{
            fontFamily: "Georgia, serif",
            fontSize: 48,
            fontWeight: "bold",
            color: currentStage.color,
            textShadow: `0 0 30px ${currentStage.color}66`,
            opacity: interpolate(stageProgress, [0, 0.2, 0.7, 1], [0, 1, 1, 0]),
          }}
        >
          {currentStage.label}
        </div>
      </AbsoluteFill>

      {/* Civilization flashes */}
      {civFlashes.map((civ) => {
        const isVisible = progress >= civ.time && progress < civ.time + 0.08;
        if (!isVisible) return null;
        return (
          <div
            key={civ.label}
            style={{
              position: "absolute",
              left: `${20 + Math.random() * 60}%`,
              top: `${30 + Math.random() * 40}%`,
              fontSize: 60,
              opacity: interpolate(
                (progress - civ.time) / 0.08,
                [0, 0.5, 1],
                [0, 1, 0]
              ),
              transform: `scale(${interpolate(
                (progress - civ.time) / 0.08,
                [0, 0.5, 1],
                [0.5, 1.5, 2]
              )})`,
            }}
          >
            {civ.emoji}
          </div>
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
          fontSize: 30,
          fontWeight: 600,
          textAlign: "center",
          textShadow: "0 2px 20px rgba(0,0,0,0.9)",
          lineHeight: 1.4,
          zIndex: 10,
          opacity: interpolate(frame, [15, 45, durationInFrames - 15, durationInFrames], [0, 1, 1, 0]),
        }}
      >
        "La vida evolucionó, y entre todas las especies, una desarrolló
        conciencia. El ser humano miró al cielo y se preguntó: ¿qué somos?"
      </div>
    </AbsoluteFill>
  );
};
