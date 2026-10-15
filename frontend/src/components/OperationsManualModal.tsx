"use client";

import React, { useState, useMemo } from "react";
import { BookOpen, Search, X, ChevronRight, CheckCircle2, AlertTriangle, ShieldCheck, Printer, ExternalLink } from "lucide-react";
import { useLocale } from "../context/LocaleContext";

interface OperationsManualModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface ManualSection {
  id: string;
  category: "getting_started" | "production" | "inventory" | "sales" | "hr" | "admin" | "troubleshooting";
  titleEn: string;
  titleNe: string;
  summaryEn: string;
  summaryNe: string;
  stepsEn: string[];
  stepsNe: string[];
  hotkeys?: string[];
  warningEn?: string;
  warningNe?: string;
}

const MANUAL_SECTIONS: ManualSection[] = [
  {
    id: "getting-started",
    category: "getting_started",
    titleEn: "1. Getting Started & Role Permissions",
    titleNe: "१. सुरुवात र प्रयोगकर्ता अनुमति",
    summaryEn: "How to log in, understand user roles (Admin, Editor, Viewer), and navigate the bilingual ERP system.",
    summaryNe: "कसरी लगइन गर्ने, भूमिकाहरू (प्रशासक, सम्पादक, दर्शक) बुझ्ने र द्विभाषी प्रणाली चलाउने।",
    stepsEn: [
      "Access the ERP system via secure credentials with assigned role.",
      "Admin: Full factory control, user management, expenses, fixed assets, and database backups.",
      "Editor: Daily shop-floor data entry, purchase orders, production batches, sales dispatches, and worker logs.",
      "Viewer: Read-only inspection mode for external auditors and statutory tax compliance checks.",
      "Toggle between English and Nepali anytime using the top-right language switcher."
    ],
    stepsNe: [
      "तोकिएको प्रयोगकर्ता नाम र गोप्य पासवर्ड प्रयोग गरी सुरक्षित लगइन गर्नुहोस्।",
      "प्रशासक (Admin): पूर्ण कारखाना नियन्त्रण, प्रयोगकर्ता व्यवस्थापन, खर्च, स्थिर सम्पत्ति, र ब्याकअप।",
      "सम्पादक (Editor): दैनिक उत्पादन दाखिला, खरिद अर्डर, बिक्री र मजदुर लग।",
      "दर्शक (Viewer): लेखापरीक्षक र कर अधिकृतहरूका लागि पढ्न मात्र मिल्ने सुरक्षित मोड।",
      "माथिल्लो दायाँ भागमा रहेको भाषा बटनबाट जुनसुकै बेला अंग्रेजी र नेपाली परिवर्तन गर्न सकिन्छ।"
    ]
  },
  {
    id: "production-batches",
    category: "production",
    titleEn: "2. Production Batch Entry (No-Mouse Shop-Floor Workflow)",
    titleNe: "२. उत्पादन ब्याच दाखिला (कीबोर्ड मात्र कार्यप्रवाह)",
    summaryEn: "Rapid entry for finished pairs across Continental sizing matrix (Sizes 32–43) without touching the mouse.",
    summaryNe: "माउस नछोइकन कन्टिनेन्टल साइज ३२–४३ मा जुत्ता उत्पादन दाखिला गर्ने द्रुत विधि।",
    stepsEn: [
      "Navigate to 'Production' from sidebar or press Alt+P.",
      "Type Article Number (e.g. LV-801) and select Color.",
      "Enter Continental size distribution from 32 to 43 using numeric keypad and Tab key.",
      "Total pairs and carton count (12 pairs = 1 carton) calculate automatically.",
      "Press Ctrl+Enter or submit button to instantly persist batch and update finished goods inventory."
    ],
    stepsNe: [
      "बायाँ मेनुबाट 'उत्पादन' मा जानुहोस् वा Alt+P थिच्नुहोस्।",
      "मोडेल नम्बर (जस्तै LV-801) र रङ छनोट गर्नुहोस्।",
      "कम्प्युटरको दायाँ नम्बर कीप्याड र Tab प्रयोग गरी साइज ३२ देखि ४३ सम्म संख्या भर्नुहोस्।",
      "जम्मा जोडी र कार्टुन संख्या (१२ जोडी = १ कार्टुन) स्वतः गणना हुनेछ।",
      "ब्याच सुरक्षित गर्न र स्टक अद्यावधिक गर्न Ctrl+Enter थिच्नुहोस्।"
    ],
    hotkeys: ["Tab (Next Size)", "Shift+Tab (Prev Size)", "Ctrl+Enter (Save Batch)"]
  },
  {
    id: "stock-ledger",
    category: "inventory",
    titleEn: "3. Stock Ledger, Multi-Location & Discrepancy Audits",
    titleNe: "३. मौज्दात खाता, बहु-स्थान र स्टक मिलान",
    summaryEn: "Track finished footwear and raw materials across Factory Main Store, Line Assembly, and Retail Branches.",
    summaryNe: "कारखाना मुख्य गोदाम, उत्पादन लाइन र शाखा पसलहरूबीच जुत्ता तथा कच्चा पदार्थको मौज्दात निगरानी।",
    stepsEn: [
      "Open 'Stock Ledger' to inspect current physical balance by article, size, and location.",
      "To transfer stock between locations: specify source, destination, and exact pair quantities.",
      "Receiving location must independently confirm incoming physical quantity to close transfer status.",
      "For damaged pairs or recount discrepancies: use 'Adjust Stock' with authorized reason and note."
    ],
    stepsNe: [
      "'मौज्दात खाता' खोलेर मोडल, साइज र स्थानअनुसार हालको स्टक हेर्नुहोस्।",
      "स्थान स्थानान्तरण गर्न: पठाउने ठाउँ, पाउने ठाउँ र संख्या प्रविष्ट गर्नुहोस्।",
      "प्राप्त गर्ने गोदामले वास्तविक गणना पुष्टि गरेपछि मात्र स्थानान्तरण सम्पन्न हुन्छ।",
      "टुटफुट वा गणना फरक परेमा: अधिकृत कारणसहित 'स्टक मिलान' सुविधा प्रयोग गर्नुहोस्।"
    ],
    warningEn: "Stock adjustments immediately update the immutable audit log with user timestamp.",
    warningNe: "स्टक मिलान गर्दा प्रयोगकर्ता र समयसहितको अडिट लग तत्काल सुरक्षित हुन्छ।"
  },
  {
    id: "sales-invoicing",
    category: "sales",
    titleEn: "4. Wholesale Dispatch & Nepal IRD Schedule-5 Tax Invoices",
    titleNe: "४. थोक बिक्री र आन्तरिक राजस्व अनुसूची-५ कर बिजक",
    summaryEn: "Generate statutory 13% VAT tax invoices with buyer PAN, carton math, and payment terms.",
    summaryNe: "ग्राहक भ्याट/प्यान, कार्टुन गणना र १३% भ्याटसहितको आधिकारिक कर बिजक जारी गर्ने विधि।",
    stepsEn: [
      "Go to 'Sales & Invoicing' and click 'New Tax Invoice'.",
      "Select Customer or enter Walk-in Buyer PAN/Name.",
      "Add footwear items with wholesale price per pair or per carton (12 pairs).",
      "13% VAT and taxable amount calculate dynamically according to Nepal IRD rules.",
      "Dispatch updates inventory automatically and records credit receivables to Customer Ledger."
    ],
    stepsNe: [
      "'बिक्री तथा बिजक' मा जानुहोस् र 'नयाँ कर बिजक' मा क्लिक गर्नुहोस्।",
      "ग्राहक छान्नुहोस् वा प्यान नम्बर र नाम प्रविष्ट गर्नुहोस्।",
      "प्रति जोडी वा प्रति कार्टुन (१२ जोडी) थोक दरमा जुत्ताका आइटम थप्नुहोस्।",
      "नेपाल आन्तरिक राजस्व नियमानुसार १३% भ्याट स्वतः हिसाब हुनेछ।",
      "बिजक जारी हुनासाथ स्टक घट्नेछ र ग्राहकको खातामा बाँकी रकम दर्ता हुनेछ।"
    ]
  },
  {
    id: "raw-materials",
    category: "production",
    titleEn: "5. Raw Materials & Purchase Procurement",
    titleNe: "५. कच्चा पदार्थ खरिद तथा खपत",
    summaryEn: "Manage soles, leather, EVA sheets, buckles, and chemical adhesives with standardized units (kg, pcs, litre).",
    summaryNe: "सोल, छाला, इभिए सिट, बकल, र गम जस्ता कच्चा पदार्थहरूको तोकिएको एकाइ (केजी, पिस, लिटर) मा व्यवस्थापन।",
    stepsEn: [
      "Access 'Purchase & Materials' to view raw material stock levels and reorder thresholds.",
      "New materials must use authorized units: 'kg', 'pcs', or 'litre' for strict database consistency.",
      "Record vendor invoices upon receipt to immediately increment raw material inventory.",
      "Production runs automatically deduct allocated BOM materials to safeguard against phantom inventory."
    ],
    stepsNe: [
      "'खरिद तथा कच्चा पदार्थ' मा गई मौज्दात र पुनर्अर्डर सीमा हेर्नुहोस्।",
      "नयाँ सामग्री दर्ता गर्दा मान्य एकाइहरू: 'kg' (केजी), 'pcs' (पिस), वा 'litre' (लिटर) मात्र छान्नुहोस्।",
      "सप्लायरको बिल प्राप्त हुनासाथ प्रविष्ट गरी स्टक बढाउनुहोस्।",
      "उत्पादन सुरु हुँदा सम्बन्धित कच्चा पदार्थ स्वचालित रूपमा कट्टा हुन्छ।"
    ]
  },
  {
    id: "hr-payroll",
    category: "hr",
    titleEn: "6. HR Worker Profiles, Advances & Monthly Payroll",
    titleNe: "६. मजदुर विवरण, पेश्की र मासिक तलब भुक्तानी",
    summaryEn: "Maintain worker profiles with photo IDs, citizenship images, daily hours, advance loans, and salary disbursements.",
    summaryNe: "कामदारको फोटो, नागरिकता प्रमाणपत्र, दैनिक काम घण्टा, पेश्की खाता र मासिक तलब भुक्तानी व्यवस्थापन।",
    stepsEn: [
      "Open 'HR Management' to view worker cards with employee ID, department, and wage rate.",
      "Log worker advances directly; deductions are automatically applied to the end-of-month pay sheet.",
      "Upload citizenship and profile pictures securely with server-side access control.",
      "Generate monthly payroll showing basic salary, hourly overtime, advance deductions, and net payable."
    ],
    stepsNe: [
      "'मानव संसाधन' मा गई कामदार परिचयपत्र, विभाग र तलब दर हेर्नुहोस्।",
      "मजदुर पेश्की तुरुन्त इन्ट्री गर्नुहोस्; महिनाको अन्त्यमा तलबबाट स्वतः कट्टी हुनेछ।",
      "नागरिकता र फोटोहरू सर्भरमा सुरक्षित रूपमा अपलोड गर्नुहोस्।",
      "आधारभूत तलब, ओभरटाइम, कट्टी गरिएको पेश्की र खुद भुक्तानी देखिने तलब सिट निकाल्नुहोस्।"
    ]
  },
  {
    id: "expenses-assets",
    category: "admin",
    titleEn: "7. Factory Expenses, Fixed Assets & Scrap Management",
    titleNe: "७. कारखाना खर्च, स्थिर सम्पत्ति र खेर गएको माल (स्क्र्याप)",
    summaryEn: "Track non-production operating overheads, heavy plant machinery, and production floor scrap reclamation.",
    summaryNe: "दैनिक कारखाना सञ्चालन खर्च, मेसिनरी स्थिर सम्पत्ति र कटिङ वेस्ट/स्क्र्याप व्यवस्थापन।",
    stepsEn: [
      "Select 'Expenses & Assets' from sidebar.",
      "Operating Expenses: Record electricity, diesel generator fuel, machine grease, rent, and transport.",
      "Fixed Assets: Maintain register for hydraulic sole presses, stitching machines, and factory generators with purchase value and serial numbers.",
      "Waste & Scrap: Record rubber trimming scrap and leather offcuts sold or recycled to balance yield calculations."
    ],
    stepsNe: [
      "बायाँ मेनुबाट 'खर्च तथा सम्पत्ति' छान्नुहोस्।",
      "सञ्चालन खर्च: बिजुली महसुल, जेनेरेटर डिजेल, मेसिन मर्मत, भाडा र ढुवानी दर्ता गर्नुहोस्।",
      "स्थिर सम्पत्ति: सोल प्रेसर मेसिन, सिलाइ मेसिन, र जेनेरेटरको खरिद मूल्य तथा सिरियल नम्बर ट्र्याक गर्नुहोस्।",
      "स्क्र्याप/वेस्ट: रबरको टुक्रा र छालाको कटिङ बिक्री वा पुनः प्रयोगको रेकर्ड राखी उत्पादन नोक्सानी हिसाब गर्नुहोस्।"
    ]
  },
  {
    id: "admin-control",
    category: "admin",
    titleEn: "8. Admin Control Center & User Access Management",
    titleNe: "८. प्रशासक कक्ष र प्रयोगकर्ता पहुँच नियन्त्रण",
    summaryEn: "Admin-only console for creating factory staff accounts, setting security roles, and resetting credentials.",
    summaryNe: "प्रशासकले मात्र नयाँ कर्मचारी खाता खोल्ने, भूमिका तोक्ने र पासवर्ड रिसेट गर्ने नियन्त्रण कक्ष।",
    stepsEn: [
      "Available only to authorized Administrators under 'Admin Control' or 'Settings'.",
      "Click 'Add New User' to provision a username, full name, email, and temporary password.",
      "Assign appropriate role: Admin (full authority), Editor (factory operator), or Viewer (auditor).",
      "Toggle status between Active and Inactive instantly to revoke access when an employee departs."
    ],
    stepsNe: [
      "प्रशासक (Admin) का लागि मात्र 'प्रशासक कक्ष' मेनुमा उपलब्ध छ।",
      "'नयाँ प्रयोगकर्ता थप्नुहोस्' मा क्लिक गरी नाम, प्रयोगकर्ता नाम र पासवर्ड राख्नुहोस्।",
      "उचित भूमिका छान्नुहोस्: प्रशासक (Admin), सम्पादक (Editor), वा दर्शक (Viewer)।",
      "कर्मचारीले काम छोडेमा तुरुन्त 'निष्क्रिय' (Inactive) बनाएर पहुँच रोक्नुहोस्।"
    ],
    warningEn: "Never share administrative credentials or disable 2-factor security policies.",
    warningNe: "प्रशासकको गोप्य पासवर्ड कसैलाई नदिनुहोस्।"
  },
  {
    id: "troubleshooting",
    category: "troubleshooting",
    titleEn: "9. Offline Support & 10-Second Troubleshooting",
    titleNe: "९. अफलाइन समर्थन र समस्या समाधान",
    summaryEn: "How the offline outbox queue protects data when factory Wi-Fi cuts out, and how to recover from issues.",
    summaryNe: "कारखानाको इन्टरनेट बन्द हुँदा डाटा सुरक्षित राख्ने अफलाइन प्रणाली र तत्काल समस्या समाधान।",
    stepsEn: [
      "When internet disconnects, a yellow badge 'Offline (X queued)' appears in the top header.",
      "Continue working normally: invoices, batches, and movements are safely queued in local encrypted storage.",
      "When network reconnects, queued transactions automatically sync to cloud database.",
      "If screen freezes or cache issues occur: press Ctrl+F5 (or Shift+Cmd+R on Mac) for a hard refresh."
    ],
    stepsNe: [
      "इन्टरनेट जाँदा माथिल्लो पट्टीमा पहेंलो 'अफलाइन (X बाँकी)' चिन्ह देखिनेछ।",
      "काम निरन्तर जारी राख्न सकिन्छ: बिल र उत्पादन ब्याच स्थानीय ब्राउजरमा सुरक्षित रहनेछन्।",
      "इन्टरनेट पुन: जोडिएपछि सबै विवरणहरू स्वतः क्लाउड डाटाबेसमा सुरक्षित हुनेछन्।",
      "कम्प्युटर रोकिएमा वा पुरानो डाटा देखिएमा: Ctrl+F5 थिचेर हार्ड रिफ्रेस गर्नुहोस्।"
    ]
  }
];

export function OperationsManualModal({ isOpen, onClose }: OperationsManualModalProps) {
  const { locale } = useLocale();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [expandedId, setExpandedId] = useState<string>("getting-started");

  const categories = [
    { id: "all", labelEn: "All Topics", labelNe: "सबै विषय" },
    { id: "getting_started", labelEn: "Getting Started", labelNe: "सुरुवात" },
    { id: "production", labelEn: "Production & Materials", labelNe: "उत्पादन तथा कच्चा माल" },
    { id: "inventory", labelEn: "Stock & Warehousing", labelNe: "मौज्दात तथा गोदाम" },
    { id: "sales", labelEn: "Sales & Invoicing", labelNe: "बिक्री तथा कर बिजक" },
    { id: "hr", labelEn: "HR & Payroll", labelNe: "मानव संसाधन तथा तलब" },
    { id: "admin", labelEn: "Admin & Assets", labelNe: "प्रशासन तथा सम्पत्ति" },
    { id: "troubleshooting", labelEn: "Troubleshooting", labelNe: "समस्या समाधान" }
  ];

  const filteredSections = useMemo(() => {
    return MANUAL_SECTIONS.filter((s) => {
      const matchesCategory = selectedCategory === "all" || s.category === selectedCategory;
      const q = searchTerm.toLowerCase().trim();
      if (!q) return matchesCategory;
      const text = `${s.titleEn} ${s.titleNe} ${s.summaryEn} ${s.summaryNe} ${s.stepsEn.join(" ")} ${s.stepsNe.join(" ")}`.toLowerCase();
      return matchesCategory && text.includes(q);
    });
  }, [searchTerm, selectedCategory]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        backgroundColor: "rgba(15, 23, 42, 0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px"
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: "#FFFFFF",
          borderRadius: "8px",
          width: "100%",
          maxWidth: "960px",
          height: "90vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.35)",
          overflow: "hidden",
          border: "1px solid #CBD5E1"
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 24px",
            borderBottom: "1px solid #E2E8F0",
            backgroundColor: "#0F172A",
            color: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ background: "#1E3A8A", padding: "8px", borderRadius: "6px" }}>
              <BookOpen size={22} color="#93C5FD" />
            </div>
            <div>
              <h2 style={{ fontSize: "16px", fontWeight: "700", margin: 0, color: "#F8FAFC" }}>
                {locale === "en" ? "LIVO Footwear ERP — Visual Operations Manual" : "LIVO जुत्ता उद्योग — कार्य सञ्चालन निर्देशिका"}
              </h2>
              <p style={{ fontSize: "11px", color: "#94A3B8", margin: "2px 0 0 0" }}>
                {locale === "en" ? "Standard Operating Procedures (SOP) & Shop-Floor Playbook • IRD Schedule-5" : "दैनिक कारखाना कार्यप्रवाह, स्टक अडिट र आन्तरिक राजस्व अनुसूची-५ निर्देशिका"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#94A3B8",
              cursor: "pointer",
              padding: "6px",
              borderRadius: "4px"
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Search & Category Tabs */}
        <div style={{ padding: "12px 24px", borderBottom: "1px solid #E2E8F0", backgroundColor: "#F8FAFC" }}>
          <div style={{ position: "relative", marginBottom: "10px" }}>
            <Search size={16} color="#64748B" style={{ position: "absolute", left: "12px", top: "10px" }} />
            <input
              type="text"
              placeholder={locale === "en" ? "Search manual by keywords (e.g. VAT, sizes 32-43, advances, offline)..." : "कुञ्जी शब्दहरू खोज्नुहोस् (जस्तै भ्याट, साइज ३२-४३, पेश्की, अफलाइन)..."}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px 8px 36px",
                borderRadius: "6px",
                border: "1px solid #CBD5E1",
                fontSize: "13px",
                outline: "none"
              }}
            />
          </div>
          <div style={{ display: "flex", gap: "6px", overflowX: "auto", paddingBottom: "4px" }}>
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                style={{
                  padding: "5px 10px",
                  fontSize: "11.5px",
                  fontWeight: selectedCategory === cat.id ? "700" : "500",
                  borderRadius: "4px",
                  border: selectedCategory === cat.id ? "1px solid #1E3A8A" : "1px solid #CBD5E1",
                  backgroundColor: selectedCategory === cat.id ? "#1E3A8A" : "#FFFFFF",
                  color: selectedCategory === cat.id ? "#FFFFFF" : "#475569",
                  cursor: "pointer",
                  whiteSpace: "nowrap"
                }}
              >
                {locale === "en" ? cat.labelEn : cat.labelNe}
              </button>
            ))}
          </div>
        </div>

        {/* Content Body */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          {/* Section List Left Bar */}
          <div style={{ width: "320px", borderRight: "1px solid #E2E8F0", overflowY: "auto", backgroundColor: "#FAFAFA" }}>
            {filteredSections.length === 0 ? (
              <div style={{ padding: "24px", textAlign: "center", color: "#64748B", fontSize: "12px" }}>
                {locale === "en" ? "No topics matched your search." : "कुनै शीर्षक भेटिएन।"}
              </div>
            ) : (
              filteredSections.map((sec) => {
                const isSelected = expandedId === sec.id;
                return (
                  <button
                    key={sec.id}
                    onClick={() => setExpandedId(sec.id)}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      padding: "12px 16px",
                      border: "none",
                      borderBottom: "1px solid #E2E8F0",
                      borderLeft: isSelected ? "4px solid #1E3A8A" : "4px solid transparent",
                      backgroundColor: isSelected ? "#EFF6FF" : "transparent",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between"
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "13px", fontWeight: isSelected ? "700" : "600", color: isSelected ? "#1E3A8A" : "#1E293B" }}>
                        {locale === "en" ? sec.titleEn : sec.titleNe}
                      </div>
                      <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "250px" }}>
                        {locale === "en" ? sec.summaryEn : sec.summaryNe}
                      </div>
                    </div>
                    <ChevronRight size={15} color={isSelected ? "#1E3A8A" : "#94A3B8"} />
                  </button>
                );
              })
            )}
          </div>

          {/* Section Details Right Pane */}
          <div style={{ flex: 1, padding: "24px 32px", overflowY: "auto", backgroundColor: "#FFFFFF" }}>
            {(() => {
              const current = MANUAL_SECTIONS.find((s) => s.id === expandedId) || MANUAL_SECTIONS[0];
              return (
                <div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px", marginBottom: "16px" }}>
                    <h3 style={{ fontSize: "18px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                      {locale === "en" ? current.titleEn : current.titleNe}
                    </h3>
                    <span style={{ fontSize: "11px", backgroundColor: "#E2E8F0", color: "#475569", padding: "3px 8px", borderRadius: "4px", fontWeight: "600", textTransform: "uppercase" }}>
                      {current.category.replace("_", " ")}
                    </span>
                  </div>

                  <p style={{ fontSize: "13.5px", color: "#334155", lineHeight: "1.6", marginBottom: "20px" }}>
                    {locale === "en" ? current.summaryEn : current.summaryNe}
                  </p>

                  {/* Hotkeys if any */}
                  {current.hotkeys && (
                    <div style={{ backgroundColor: "#F1F5F9", padding: "10px 14px", borderRadius: "6px", marginBottom: "18px", display: "flex", alignItems: "center", gap: "10px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "700", color: "#1E293B" }}>{locale === "en" ? "QUICK HOTKEYS:" : "द्रुत सर्टकटहरू:"}</span>
                      <div style={{ display: "flex", gap: "6px" }}>
                        {current.hotkeys.map((h, i) => (
                          <kbd key={i} style={{ backgroundColor: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "2px 6px", fontSize: "11px", fontWeight: "600", color: "#0F172A" }}>
                            {h}
                          </kbd>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Step by Step SOP */}
                  <h4 style={{ fontSize: "13px", fontWeight: "700", color: "#1E3A8A", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>
                    {locale === "en" ? "Standard Operating Procedure (SOP):" : "मानक कार्य सञ्चालन प्रक्रिया (SOP):"}
                  </h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "20px" }}>
                    {(locale === "en" ? current.stepsEn : current.stepsNe).map((step, idx) => (
                      <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                        <div style={{ minWidth: "22px", height: "22px", borderRadius: "50%", backgroundColor: "#EFF6FF", border: "1px solid #BFDBFE", color: "#1D4ED8", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: "700", marginTop: "2px" }}>
                          {idx + 1}
                        </div>
                        <div style={{ fontSize: "13px", color: "#1E293B", lineHeight: "1.5" }}>
                          {step}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Warning / Callout */}
                  {(current.warningEn || current.warningNe) && (
                    <div style={{ backgroundColor: "#FEF2F2", border: "1px solid #FECACA", borderRadius: "6px", padding: "12px 14px", display: "flex", alignItems: "center", gap: "10px" }}>
                      <AlertTriangle size={18} color="#DC2626" />
                      <div style={{ fontSize: "12px", color: "#991B1B", fontWeight: "500" }}>
                        {locale === "en" ? current.warningEn : current.warningNe}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: "10px 24px", borderTop: "1px solid #E2E8F0", backgroundColor: "#F8FAFC", display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "11px", color: "#64748B" }}>
          <div>
            Livo Footwear Industries Pvt. Ltd. • IRD PAN: 609823412
          </div>
          <button
            onClick={onClose}
            style={{
              padding: "6px 14px",
              backgroundColor: "#1E3A8A",
              color: "#FFFFFF",
              border: "none",
              borderRadius: "4px",
              fontWeight: "600",
              cursor: "pointer",
              fontSize: "12px"
            }}
          >
            {locale === "en" ? "Close Manual" : "म्यानुअल बन्द गर्नुहोस्"}
          </button>
        </div>
      </div>
    </div>
  );
}
