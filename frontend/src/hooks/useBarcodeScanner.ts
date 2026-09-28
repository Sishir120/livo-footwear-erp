import { useEffect, useRef } from "react";

/**
 * Hook to capture rapid hardware keystrokes from USB/Bluetooth HID Barcode Scanners.
 * Distinguishes scanner input from human typing using inter-keystroke intervals (< 35ms).
 */
export function useBarcodeScanner(onScan: (barcode: string) => void, enabled: boolean = true) {
  const bufferRef = useRef<string[]>([]);
  const lastKeyTimeRef = useRef<number>(0);

  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore modifier keys
      if (e.ctrlKey || e.altKey || e.metaKey) return;

      const now = Date.now();
      const interval = now - lastKeyTimeRef.current;
      lastKeyTimeRef.current = now;

      if (e.key === "Enter") {
        if (bufferRef.current.length >= 3) {
          const barcode = bufferRef.current.join("").trim();
          if (barcode.length >= 3) {
            e.preventDefault();
            e.stopPropagation();
            onScan(barcode);
          }
        }
        bufferRef.current = [];
        return;
      }

      // Scanner chars arrive at < 35ms intervals; if human paused > 45ms, reset buffer
      if (interval > 45) {
        bufferRef.current = [];
      }

      // Printable single character
      if (e.key.length === 1) {
        bufferRef.current.push(e.key);
      }
    };

    window.addEventListener("keydown", handleKeyDown, true);
    return () => {
      window.removeEventListener("keydown", handleKeyDown, true);
    };
  }, [onScan, enabled]);
}
