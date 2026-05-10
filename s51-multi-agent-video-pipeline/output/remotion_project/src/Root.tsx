import { Composition } from "remotion";
import { UniverseVideo } from "./UniverseVideo";

// 9:16 format for Shorts
const FPS = 30;
const DURATION = 60; // seconds

export const Root: React.FC = () => {
  return (
    <Composition
      id="UniverseVideo"
      component={UniverseVideo}
      durationInFrames={DURATION * FPS}
      fps={FPS}
      width={1080}
      height={1920}
    />
  );
};
