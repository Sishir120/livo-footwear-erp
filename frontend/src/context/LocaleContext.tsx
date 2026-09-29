"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

export type Locale = "en" | "ne";

export const translations: Record<Locale, Record<string, string>> = {
  en: {
    // Nav & Tabs
    dashboard: "Daily Report",
    stock_ledger: "Stock Ledger",
    ar_aging: "Party Aging & Subledger",
    production_batches: "Production Batches",
    purchase_raw_materials: "Raw Material Purchases",
    sales_invoicing: "Sales & Invoicing",
    settings_backups: "Settings & Diagnostics",
    ops_cockpit: "Ops Cockpit (सुपरभाइजर ककपिट)",

    // Titles
    daily_summary_title: "Daily Operational Summary",
    daily_summary_desc: "Real-time consolidated view of factory production, wholesale dispatches, and ledger cash flow",
    stock_ledger_title: "Finished Footwear Inventory Ledger",
    stock_ledger_desc: "Derived in real-time from immutable append-only stock movements. Zero direct balance edits.",
    production_title: "Factory Assembly & Production Runs",
    production_desc: "Real-time production tracking with automatic finished goods ledger increments",
    purchases_title: "Raw Material Procurement Ledger",
    purchases_desc: "Factory inward ledger for materials, leather, outsoles, and supplier invoices",
    sales_title: "Sales Orders & Issued Sequential Invoices",
    sales_desc: "Non-resettable, gapless sequential invoice numbers enforced by PostgreSQL UniqueConstraint",
    settings_title: "System Settings & Database Backups",
    settings_desc: "Manage encrypted cloud snapshots, audit logs, and system diagnostics",

    // Metrics & Badges
    pairs: "pairs",
    pairs_in_hand: "Pairs in Hand",
    healthy: "HEALTHY",
    low_stock: "LOW STOCK",
    out_of_stock: "OUT OF STOCK",
    tax_invoice: "Tax Invoice",
    vat_tax_invoice: "Tax Invoice (VAT)",
    total_products: "Total SKU Items",
    total_stock_volume: "Total Stock Volume",
    total_stock_value: "Estimated Stock Value",
    production_output: "Daily Finished Output",
    active_workers: "Active Assembly Workers",
    gross_sales: "Gross Wholesale Dispatches",
    cash_received: "Cash Received",
    accounts_receivable: "Accounts Receivable",

    // Common Actions & Form Controls
    record_purchase: "Record Raw Material Purchase",
    issue_batch: "Issue Production Batch",
    record_sale: "Record Sale & Issue Invoice",
    continuous_mode: "Continuous Rapid Entry Mode",
    commit_record: "Commit Record",
    commit_close: "Commit & Close",
    commit_next_batch: "Commit & Next Batch ↵",
    commit_next_purchase: "Commit & Next Purchase ↵",
    commit_next_sale: "Commit & Next Invoice ↵",
    close: "Close",
    export_excel: "Download Excel / CSV",
    void_action: "Void",
    voided_badge: "VOID",
    search_placeholder: "Search records, codes, clients, suppliers...",
    login_title: "Enterprise Footwear ERP",
    login_subtitle: "Multi-tenant inventory, size-break analytics & immutable invoicing",
    username: "Username",
    password: "Password",
    login_button: "Sign In to ERP System",
    logout: "Logout",
    role_editor: "EDITOR ROLE",
    role_viewer: "VIEWER ROLE",
    supplier: "Supplier / Vendor",
    raw_material: "Raw Material Item",
    quantity: "Quantity",
    unit_rate: "Unit Rate (Rs.)",
    date_ad: "Date (AD)",
    date_bs: "Date (BS)",
    remarks: "Remarks / Gate Pass No.",
    physical_bill: "Supplier Physical Bill / Receipt (Photo or PDF)",
    click_upload: "Click to upload physical vendor bill / voucher",
    upload_hint: "PNG, JPG, or PDF up to 10MB for visual audit verification",
    footwear_model: "Footwear Model (Size / Color Code)",
    target_pairs: "Target Pairs",
    produced_pairs: "Finished Produced Pairs",
    assembly_workers: "Assembly Workers",
    batch_no: "Batch Serial Number",
    order_no: "Sales Order Number",
    client_buyer: "Client / Buyer Name",
    invoice_no: "Invoice No.",
    invoice_total: "Invoice Total",
    print_action: "Print Action",
    all_categories: "All Categories",
    filter_by_supplier: "Filter by Supplier:",
    all_suppliers: "All Suppliers",
    all_clients: "All Clients",
    shortcuts_hint: "Esc close • Ctrl+Enter quick commit"
  },
  ne: {
    // Nav & Tabs
    dashboard: "दैनिक प्रतिवेदन",
    stock_ledger: "स्टक खाता / मौज्दात",
    ar_aging: "पार्टी हिसाव तथा बक्यौता",
    production_batches: "उत्पादन ब्याच",
    purchase_raw_materials: "कच्चा पदार्थ खरिद",
    sales_invoicing: "बिक्री तथा बिलिङ",
    settings_backups: "सेटिङ तथा ब्याकअप",
    ops_cockpit: "सुपरभाइजर ककपिट (Ops Cockpit)",

    // Titles
    daily_summary_title: "दैनिक कार्यसञ्चालन प्रतिवेदन",
    daily_summary_desc: "कारखाना उत्पादन, थोक बिक्री निकासी तथा नगद प्रवाहको वास्तविक विवरण",
    stock_ledger_title: "तयारी जुत्ता-चप्पल मौज्दात खाता",
    stock_ledger_desc: "अपरिवर्तनीय स्टक मुभमेन्ट लेजरबाट स्वतः गणना हुने प्रत्यक्ष मौज्दात विवरण",
    production_title: "कारखाना उत्पादन तथा ब्याच सञ्चालन",
    production_desc: "तयारी सामानको खातामा स्वतः वृद्धि हुने वास्तविक उत्पादन ट्र्याकिङ",
    purchases_title: "कच्चा पदार्थ खरिद तथा भन्सार खाता",
    purchases_desc: "छाला, सोल तथा अन्य कच्चा पदार्थको गेट इन्ट्री र आपूर्तिकर्ता बिल विवरण",
    sales_title: "थोक बिक्री आदेश तथा क्रमिक कर बिजक",
    sales_desc: "नेपाल सरकारको भ्याट नियम अनुसार गैर-परिवर्तनीय क्रमिक कर बिजक प्रणाली",
    settings_title: "प्रणाली सेटिङ तथा डाटा ब्याकअप",
    settings_desc: "क्लाउड डाटाबेस ब्याकअप, अडिट लग तथा प्रणाली निरीक्षण विवरण",

    // Metrics & Badges
    pairs: "जोडी",
    pairs_in_hand: "हाल मौज्दात",
    healthy: "सम्पन्न / पर्याप्त",
    low_stock: "न्यून मौज्दात",
    out_of_stock: "स्टक समाप्त",
    tax_invoice: "कर बिजक",
    vat_tax_invoice: "कर बिजक (भ्याट)",
    total_products: "कुल उत्पादन प्रकार (SKU)",
    total_stock_volume: "कुल मौज्दात परिमाण",
    total_stock_value: "अनुमानित स्टक मूल्य",
    production_output: "दैनिक कुल उत्पादन",
    active_workers: "सक्रिय कामदार संख्या",
    gross_sales: "कुल थोक बिक्री",
    cash_received: "नगद प्राप्त रकम",
    accounts_receivable: "उठ्न बाँकी रकम (बक्यौता)",

    // Common Actions & Form Controls
    record_purchase: "कच्चा पदार्थ खरिद दर्ता",
    issue_batch: "नयाँ उत्पादन ब्याच सुरु",
    record_sale: "बिक्री दर्ता तथा बिलिङ",
    continuous_mode: "निरन्तर द्रुत प्रविष्टि मोड",
    commit_record: "सुरक्षित गर्नुहोस्",
    commit_close: "सेभ गरी बन्द गर्नुहोस्",
    commit_next_batch: "सेभ गरी अर्को ब्याच ↵",
    commit_next_purchase: "सेभ गरी अर्को खरिद ↵",
    commit_next_sale: "सेभ गरी अर्को बिल ↵",
    close: "बन्द गर्नुहोस्",
    export_excel: "एक्सेल / CSV डाउनलोड",
    void_action: "रद्द गर्नुहोस्",
    voided_badge: "रद्द गरिएको",
    search_placeholder: "खोज्नुहोस् (कोड, ग्राहक, आपूर्तिकर्ता, मिति)...",
    login_title: "लिभो फुटवेयर ईआरपी",
    login_subtitle: "उत्पादन, मौज्दात विश्लेषण तथा क्रमिक कर बिलिङ प्रणाली",
    username: "प्रयोगकर्ता नाम",
    password: "गोप्य संकेत (पासवर्ड)",
    login_button: "ईआरपीमा लगइन गर्नुहोस्",
    logout: "बाहिरिनुहोस्",
    role_editor: "सम्पादक (एडिटर)",
    role_viewer: "दर्शक (भ्यूअर)",
    supplier: "आपूर्तिकर्ता / भेन्डर",
    raw_material: "कच्चा पदार्थ",
    quantity: "परिमाण",
    unit_rate: "दर (रु.)",
    date_ad: "मिति (ई.सं. AD)",
    date_bs: "मिति (वि.सं. BS)",
    remarks: "कैफियत / गेट पास नं.",
    physical_bill: "आपूर्तिकर्ताको भौतिक बिल / भर्पाई (फोटो वा PDF)",
    click_upload: "भौतिक बिल / भौचर अपलोड गर्न यहाँ थिच्नुहोस्",
    upload_hint: "१० MB सम्मको PNG, JPG वा PDF सुरक्षित अडिटका लागि",
    footwear_model: "जुत्ता मोडल (साइज / रङ कोड)",
    target_pairs: "लक्षित परिमाण (जोडी)",
    produced_pairs: "तयार भएको परिमाण (जोडी)",
    assembly_workers: "कामदार संख्या",
    batch_no: "ब्याच संकेत नं.",
    order_no: "बिक्री आदेश नं.",
    client_buyer: "ग्राहक / खरिदकर्ताको नाम",
    invoice_no: "कर बिजक नं.",
    invoice_total: "कुल बिल रकम",
    print_action: "प्रिन्ट",
    all_categories: "सबै वर्गहरू",
    filter_by_supplier: "आपूर्तिकर्ता अनुसार छान्नुहोस्:",
    all_suppliers: "सबै आपूर्तिकर्ताहरू",
    all_clients: "सबै ग्राहकहरू",
    shortcuts_hint: "Esc बन्द • Ctrl+Enter द्रुत सेभ"
  }
};

interface LocaleContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
  t: (key: string, fallback?: string) => string;
}

const LocaleContext = createContext<LocaleContextType>({
  locale: "en",
  setLocale: () => {},
  toggleLocale: () => {},
  t: (key: string, fallback?: string) => fallback || key,
});

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("livo_locale") as Locale;
      if (saved === "en" || saved === "ne") {
        setLocaleState(saved);
      }
    } catch (e) {
      // localStorage unavailable or restricted
    }
  }, []);

  const setLocale = (newLocale: Locale) => {
    setLocaleState(newLocale);
    try {
      localStorage.setItem("livo_locale", newLocale);
    } catch (e) {
      // ignore
    }
  };

  const toggleLocale = () => {
    setLocale(locale === "en" ? "ne" : "en");
  };

  const t = (key: string, fallback?: string): string => {
    const dict = translations[locale];
    if (dict && dict[key]) {
      return dict[key];
    }
    const enDict = translations["en"];
    if (enDict && enDict[key]) {
      return enDict[key];
    }
    return fallback !== undefined ? fallback : key;
  };

  return (
    <LocaleContext.Provider value={{ locale, setLocale, toggleLocale, t }}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  return useContext(LocaleContext);
}
