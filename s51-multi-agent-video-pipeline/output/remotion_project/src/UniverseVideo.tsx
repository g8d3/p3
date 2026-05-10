import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from "remotion";
import { Scene1 } from "./scenes/Scene1";
import { Scene2 } from "./scenes/Scene2";
import { Scene3 } from "./scenes/Scene3";
import { Scene4 } from "./scenes/Scene4";
import { Scene5 } from "./scenes/Scene5";
import { Scene6 } from "./scenes/Scene6";

const FPS = 30;

interface SceneConfig {
  id: number;
  durationFrames: number;
  component: React.FC<{ frame: number; durationInFrames: number }>;
}

// Scene timing in frames at 30fps
const scenes: SceneConfig[] = [
  { id: 1, durationFrames: 8 * FPS, component: Scene1 },
  { id: 2, durationFrames: 12 * FPS, component: Scene2 },
  { id: 3, durationFrames: 8 * FPS, component: Scene3 },
  { id: 4, durationFrames: 12 * FPS, component: Scene4 },
  { id: 5, durationFrames: 8 * FPS, component: Scene5 },
  { id: 6, durationFrames: 12 * FPS, component: Scene6 },
];

// Accumulated start frames for each scene
function getStartFrame(sceneIndex: number): number {
  let start = 0;
  for (let i = 0; i < sceneIndex; i++) {
    start += scenes[i].durationFrames;
  }
  return start;
}

const TRANSITION_FRAMES = 15; // 0.5s transition

export const UniverseVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const totalFrames = scenes.reduce((acc, s) => acc + s.durationFrames, 0);

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {scenes.map((scene, idx) => {
        const startFrame = getStartFrame(idx);
        const endFrame = startFrame + scene.durationFrames;

        // Calculate a global opacity for transition blending
        const sceneLocalFrame = frame - startFrame;
        let opacity = 1;

        // Fade in at the start of this scene
        if (sceneLocalFrame >= 0 && sceneLocalFrame < TRANSITION_FRAMES && idx > 0) {
          opacity = interpolate(sceneLocalFrame, [0, TRANSITION_FRAMES], [0, 1], {
            extrapolateRight: "clamp",
          });
        }
        // Fade out at the end of this scene
        else if (
          sceneLocalFrame >= scene.durationFrames - TRANSITION_FRAMES &&
          sceneLocalFrame < scene.durationFrames &&
          idx < scenes.length - 1
        ) {
          opacity = interpolate(
            sceneLocalFrame,
            [scene.durationFrames - TRANSITION_FRAMES, scene.durationFrames],
            [1, 0],
            { extrapolateLeft: "clamp" }
          );
        }

        if (sceneLocalFrame < 0 || sceneLocalFrame >= scene.durationFrames) {
          opacity = 0;
        }

        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={scene.durationFrames}
            name={`Scene ${scene.id}`}
          >
            <div
              style={{
                width: "100%",
                height: "100%",
                opacity,
                position: "absolute",
                top: 0,
                left: 0,
              }}
            >
              <scene.component
                frame={sceneLocalFrame}
                durationInFrames={scene.durationFrames}
              />
            </div>
          </Sequence>
        );
      })}

      {/* Letterbox bars for cinematic look */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 120,
          backgroundColor: "black",
          zIndex: 100,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 120,
          backgroundColor: "black",
          zIndex: 100,
        }}
      />
    </AbsoluteFill>
  );
};
