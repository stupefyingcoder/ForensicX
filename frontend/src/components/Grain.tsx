export function Grain() {
  return (
    <div className="grain-overlay">
      <svg style={{ position: "absolute", top: "-50%", left: "-50%", width: "200%", height: "200%" }}>
        <filter id="forensicx-grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves={3} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#forensicx-grain)" />
      </svg>
    </div>
  );
}
