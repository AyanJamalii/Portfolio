"use client";

import { useEffect, useRef } from "react";

const HOVER_SELECTOR =
  "a, button, [role='button'], summary, select, label[for], [data-cursor='hover']";
const TEXT_SELECTOR = "input, textarea, [contenteditable='true']";

export default function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Only for devices with a real mouse
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;

    const dot = dotRef.current;
    const ring = ringRef.current;
    if (!dot || !ring) return;

    const root = document.documentElement;
    const ease = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 1 : 0.18;
    root.classList.add("has-custom-cursor");

    let targetX = 0;
    let targetY = 0;
    let ringX = 0;
    let ringY = 0;
    let frame = 0;
    let seen = false; // the mouse has moved at least once
    let inText = false; // hovering a text field: show the normal text cursor
    let outside = false; // the mouse left the window
    let visible = false;

    const sync = () => {
      const want = seen && !inText && !outside;
      if (want === visible) return;
      visible = want;
      dot.classList.toggle("is-visible", want);
      ring.classList.toggle("is-visible", want);
    };

    const render = () => {
      ringX += (targetX - ringX) * ease;
      ringY += (targetY - ringY) * ease;
      ring.style.transform = `translate3d(${ringX}px, ${ringY}px, 0)`;
      const moving = Math.abs(targetX - ringX) > 0.1 || Math.abs(targetY - ringY) > 0.1;
      frame = moving ? requestAnimationFrame(render) : 0;
    };

    const onMove = (e: MouseEvent) => {
      targetX = e.clientX;
      targetY = e.clientY;
      dot.style.transform = `translate3d(${targetX}px, ${targetY}px, 0)`;
      if (!seen) {
        seen = true;
        ringX = targetX;
        ringY = targetY;
      }
      if (!frame) frame = requestAnimationFrame(render);
      sync();
    };

    const onOver = (e: MouseEvent) => {
      const el = e.target as Element | null;
      const hovering = !!el?.closest(HOVER_SELECTOR);
      inText = !!el?.closest(TEXT_SELECTOR);
      dot.classList.toggle("is-hover", hovering);
      ring.classList.toggle("is-hover", hovering);
      sync();
    };

    const onDown = () => {
      dot.classList.add("is-pressed");
      ring.classList.add("is-pressed");
    };
    const onUp = () => {
      dot.classList.remove("is-pressed");
      ring.classList.remove("is-pressed");
    };
    const onLeave = () => {
      outside = true;
      sync();
    };
    const onEnter = () => {
      outside = false;
      sync();
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("mouseover", onOver, { passive: true });
    window.addEventListener("mousedown", onDown);
    window.addEventListener("mouseup", onUp);
    root.addEventListener("mouseleave", onLeave);
    root.addEventListener("mouseenter", onEnter);

    return () => {
      cancelAnimationFrame(frame);
      root.classList.remove("has-custom-cursor");
      window.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseover", onOver);
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("mouseup", onUp);
      root.removeEventListener("mouseleave", onLeave);
      root.removeEventListener("mouseenter", onEnter);
    };
  }, []);

  return (
    <>
      <div ref={ringRef} className="cursor cursor-ring" aria-hidden="true">
        <span />
      </div>
      <div ref={dotRef} className="cursor cursor-dot" aria-hidden="true">
        <span />
      </div>
    </>
  );
}