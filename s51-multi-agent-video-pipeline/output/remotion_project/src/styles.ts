import React from "react";

// Shared CSS styles
export const CONTAINER_STYLE: React.CSSProperties = {
  width: "100%",
  height: "100%",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  overflow: "hidden",
  position: "relative",
};

export const DIALOGO_STYLE: React.CSSProperties = {
  position: "absolute",
  bottom: 120,
  left: 60,
  right: 60,
  color: "white",
  fontFamily: "Helvetica, Arial, sans-serif",
  fontSize: 36,
  fontWeight: 600,
  textAlign: "center",
  textShadow: "0 2px 20px rgba(0,0,0,0.8)",
  lineHeight: 1.4,
  zIndex: 10,
};

export const TITLE_STYLE: React.CSSProperties = {
  fontFamily: "Georgia, serif",
  fontSize: 48,
  fontWeight: "bold",
  color: "white",
  textShadow: "0 4px 30px rgba(0,0,0,0.9)",
  textAlign: "center",
};

export const LETTERBOX_HEIGHT = 120;

export const letterboxStyle: React.CSSProperties = {
  position: "absolute",
  left: 0,
  right: 0,
  height: LETTERBOX_HEIGHT,
  backgroundColor: "black",
  zIndex: 100,
};
