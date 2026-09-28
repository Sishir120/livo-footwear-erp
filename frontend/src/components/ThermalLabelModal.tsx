import React, { useState } from "react";
import { Printer, Download, X, Copy, Check } from "lucide-react";

export interface BoxLabelData {
  productName: string;
  sku: string;
  size: string;
  color?: string;
  batchNumber: string;
  companyPan?: string;
  dateStr?: string;
}

interface ThermalLabelModalProps {
  isOpen: boolean;
  onClose: () => void;
  labelData: BoxLabelData;
}

/**
 * Lightweight Code 128-B barcode pattern generator for standard shoe box labels.
 * Produces crisp vector SVG bars without external dependencies.
 */
function generateCode128BPattern(text: string): number[] {
  // Subset of standard Code 128 widths [b1, s1, b2, s2, b3, s3]
  const table: { [char: string]: number[] } = {
    " ": [2, 1, 2, 2, 2, 2], "!": [2, 2, 2, 1, 2, 2], '"': [2, 2, 2, 2, 2, 1],
    "#": [1, 2, 1, 2, 2, 3], "$": [1, 2, 1, 3, 2, 2], "%": [1, 3, 1, 2, 2, 2],
    "&": [1, 2, 2, 2, 1, 3], "'": [1, 2, 2, 3, 1, 2], "(": [1, 3, 2, 2, 1, 2],
    ")": [2, 2, 1, 2, 1, 3], "*": [2, 2, 1, 3, 1, 2], "+": [2, 3, 1, 2, 1, 2],
    ",": [1, 1, 2, 2, 3, 2], "-": [1, 2, 2, 1, 3, 2], ".": [1, 2, 2, 2, 3, 1],
    "/": [1, 1, 3, 2, 2, 2], "0": [1, 2, 3, 1, 2, 2], "1": [1, 2, 3, 2, 2, 1],
    "2": [2, 2, 3, 2, 1, 1], "3": [2, 2, 1, 1, 3, 2], "4": [2, 2, 1, 2, 3, 1],
    "5": [2, 1, 3, 2, 1, 2], "6": [2, 2, 3, 1, 1, 2], "7": [3, 1, 2, 1, 3, 1],
    "8": [3, 1, 1, 2, 2, 2], "9": [3, 2, 1, 1, 2, 2], ":": [3, 2, 1, 2, 2, 1],
    ";": [3, 1, 2, 2, 1, 2], "<": [3, 2, 2, 1, 1, 2], "=": [3, 2, 2, 2, 1, 1],
    ">": [2, 1, 2, 1, 2, 3], "?": [2, 1, 2, 3, 2, 1], "@": [2, 3, 2, 1, 2, 1],
    "A": [1, 1, 1, 3, 2, 3], "B": [1, 3, 1, 1, 2, 3], "C": [1, 3, 1, 3, 2, 1],
    "D": [1, 1, 2, 3, 1, 3], "E": [1, 3, 2, 1, 1, 3], "F": [1, 3, 2, 3, 1, 1],
    "G": [2, 1, 1, 3, 1, 3], "H": [2, 3, 1, 1, 1, 3], "I": [2, 3, 1, 3, 1, 1],
    "J": [1, 1, 2, 1, 3, 3], "K": [1, 1, 2, 3, 3, 1], "L": [1, 3, 2, 1, 3, 1],
    "M": [1, 1, 3, 1, 2, 3], "N": [1, 1, 3, 3, 2, 1], "O": [1, 3, 3, 1, 2, 1],
    "P": [3, 1, 3, 1, 2, 1], "Q": [2, 1, 1, 3, 3, 1], "R": [2, 3, 1, 1, 3, 1],
    "S": [2, 1, 3, 1, 1, 3], "T": [2, 1, 3, 3, 1, 1], "U": [2, 1, 3, 1, 3, 1],
    "V": [3, 1, 1, 1, 2, 3], "W": [3, 1, 1, 3, 2, 1], "X": [3, 3, 1, 1, 2, 1],
    "Y": [3, 1, 2, 1, 1, 3], "Z": [3, 1, 2, 3, 1, 1], "_": [1, 1, 1, 2, 2, 4],
  };

  const startB = [2, 1, 1, 2, 1, 4];
  const stop = [2, 3, 3, 1, 1, 1, 2];
  const widths: number[] = [...startB];

  for (const ch of text.toUpperCase()) {
    const pattern = table[ch] || table["-"] || [1, 2, 2, 1, 3, 2];
    widths.push(...pattern);
  }
  widths.push(...stop);
  return widths;
}

export function ThermalLabelModal({ isOpen, onClose, labelData }: ThermalLabelModalProps) {
  const [copied, setCopied] = useState(false);
  const [outputTab, setOutputTab] = useState<"preview" | "escpos">("preview");

  if (!isOpen) return null;

  const barcodeString = labelData.sku || labelData.batchNumber || "LIVO-DEFAULT";
  const widths = generateCode128BPattern(barcodeString);
  const totalUnits = widths.reduce((a, b) => a + b, 0);

  // SVG bars
  let currentX = 0;
  const bars: { x: number; width: number }[] = [];
  widths.forEach((w, index) => {
    if (index % 2 === 0) {
      bars.push({ x: currentX, width: w });
    }
    currentX += w;
  });

  // ESC/POS Command Generation (Binary format for thermal receipt/label printers)
  const generateEscPosData = (): string => {
    return [
      "\\x1B\\x40", // Initialize printer
      "\\x1B\\x61\\x01", // Center alignment
      `\\x1B\\x45\\x01${labelData.productName.toUpperCase()}\\x1B\\x45\\x00\\x0A`,
      `\\x1D\\x21\\x11SIZE: ${labelData.size}\\x1D\\x21\\x00\\x0A`,
      `SKU: ${labelData.sku} | BATCH: ${labelData.batchNumber}\\x0A`,
      `PAN: ${labelData.companyPan || "609823412"} | DATE: ${labelData.dateStr || new Date().toISOString().split("T")[0]}\\x0A`,
      "\\x1D\\x77\\x02\\x1D\\x68\\x40", // Barcode width 2, height 64
      `\\x1D\\x6B\\x49${String.fromCharCode(barcodeString.length)}${barcodeString}\\x0A`,
      "\\x0A\\x0A\\x1D\\x56\\x00" // Cut paper
    ].join("");
  };

  const handlePrint = () => {
    window.print();
  };

  const handleCopyEscPos = () => {
    navigator.clipboard.writeText(generateEscPosData());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 w-full max-w-lg rounded-md shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-950">
          <div className="flex items-center gap-2">
            <Printer className="w-5 h-5 text-emerald-400" />
            <h3 className="font-semibold text-slate-100 text-sm tracking-wide">
              Shoe Box Thermal Label Generator (2" × 1")
            </h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200 p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-slate-800 bg-slate-900 px-4 pt-2 gap-4 text-xs font-medium">
          <button
            onClick={() => setOutputTab("preview")}
            className={`pb-2 border-b-2 transition-colors ${
              outputTab === "preview" ? "border-emerald-500 text-emerald-400" : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Visual Label Preview (@media print)
          </button>
          <button
            onClick={() => setOutputTab("escpos")}
            className={`pb-2 border-b-2 transition-colors ${
              outputTab === "escpos" ? "border-emerald-500 text-emerald-400" : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Raw ESC/POS WebUSB Payload
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex flex-col items-center justify-center bg-slate-950/60 min-h-[220px]">
          {outputTab === "preview" ? (
            <div
              id="printable-thermal-label"
              className="w-[288px] h-[144px] bg-white text-black p-2.5 rounded-sm shadow-md flex flex-col justify-between border border-slate-300 font-sans select-none"
            >
              {/* Top Row: Article Name & Big Size */}
              <div className="flex justify-between items-start leading-tight">
                <div className="overflow-hidden pr-1">
                  <div className="text-[11px] font-black uppercase truncate tracking-tight">
                    {labelData.productName || "LIVO FOOTWEAR"}
                  </div>
                  <div className="text-[9px] font-semibold text-gray-700">
                    {labelData.color ? `${labelData.color} · ` : ""}BATCH: {labelData.batchNumber}
                  </div>
                </div>
                <div className="bg-black text-white px-1.5 py-0.5 rounded text-[15px] font-black tracking-tight shrink-0 font-mono">
                  SZ {labelData.size}
                </div>
              </div>

              {/* Barcode Vector Area */}
              <div className="flex flex-col items-center my-0.5">
                <svg
                  viewBox={`0 0 ${totalUnits} 32`}
                  className="w-full h-8"
                  preserveAspectRatio="none"
                >
                  {bars.map((bar, i) => (
                    <rect key={i} x={bar.x} y={0} width={bar.width} height={32} fill="black" />
                  ))}
                </svg>
                <span className="text-[8px] font-mono tracking-widest font-bold mt-0.5">
                  *{barcodeString}*
                </span>
              </div>

              {/* Footer Row */}
              <div className="flex justify-between items-center text-[7.5px] font-mono text-gray-600 border-t border-gray-300 pt-0.5">
                <span>PAN: {labelData.companyPan || "609823412"}</span>
                <span>{labelData.dateStr || new Date().toISOString().split("T")[0]}</span>
                <span className="font-bold text-black">MADE IN NEPAL</span>
              </div>
            </div>
          ) : (
            <div className="w-full bg-slate-900 border border-slate-800 rounded p-3 text-xs font-mono text-slate-300 overflow-x-auto max-h-[144px]">
              <pre className="whitespace-pre-wrap">{generateEscPosData()}</pre>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800 bg-slate-950">
          <span className="text-xs text-slate-400">
            Standard 58mm/80mm Thermal Receipt & Label
          </span>
          <div className="flex gap-2">
            {outputTab === "preview" ? (
              <button
                onClick={handlePrint}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold shadow transition-colors"
              >
                <Printer className="w-3.5 h-3.5" />
                Print Box Label
              </button>
            ) : (
              <button
                onClick={handleCopyEscPos}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold border border-slate-700 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? "Copied" : "Copy Hex String"}
              </button>
            )}
            <button
              onClick={onClose}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs font-medium border border-slate-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
