"use client";

import React, { useState, useEffect } from "react";
import {
  Image as ImageIcon,
  Search,
  Plus,
  RefreshCw,
  Download,
  Trash2,
  X,
  AlertCircle,
  Eye,
  Tag,
  Upload,
  Layers,
  CheckCircle2
} from "lucide-react";
import { useLocale } from "@/context/LocaleContext";

interface ProductGalleryViewProps {
  userRole: string;
}

interface GalleryItem {
  id: number;
  company_id: number;
  product_id: number;
  product_code: string;
  product_name: string;
  category: string | null;
  image_url: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number | null;
  is_primary: boolean;
  created_at: string;
}

interface ProductOption {
  id: number;
  code: string;
  name: string;
  category: string | null;
}

export function ProductGalleryView({ userRole }: ProductGalleryViewProps) {
  const { isNepali, t } = useLocale();
  const isViewer = userRole === "viewer";

  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<GalleryItem[]>([]);
  const [products, setProducts] = useState<ProductOption[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");

  // Modals
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [previewImageModal, setPreviewImageModal] = useState<GalleryItem | null>(null);

  // Upload state
  const [uploadProductId, setUploadProductId] = useState<number | "">("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreviewUrl, setFilePreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Fetch Gallery Items
  const fetchGallery = async () => {
    setLoading(true);
    setError(null);
    try {
      let url = "/api/v1/gallery";
      const params = new URLSearchParams();
      if (categoryFilter !== "ALL") params.append("category", categoryFilter);
      if (searchTerm.trim()) params.append("search", searchTerm.trim());
      const queryStr = params.toString();
      if (queryStr) url += `?${queryStr}`;

      const res = await fetch(url);
      if (!res.ok) throw new Error(`Failed to load gallery: ${res.statusText}`);
      const data = await res.json();
      setItems(data);
    } catch (err: any) {
      setError(err.message || "Failed to load product gallery");
    } finally {
      setLoading(false);
    }
  };

  // Fetch Products for Upload Select
  const fetchProducts = async () => {
    try {
      const res = await fetch("/api/v1/stock/ledger");
      if (res.ok) {
        const data = await res.json();
        const prods: ProductOption[] = (data.ledger || data || []).map((p: any) => ({
          id: p.product_id || p.id,
          code: p.product_code || p.code,
          name: p.product_name || p.name,
          category: p.category || null
        }));
        // Remove duplicates by ID
        const unique = Array.from(new Map(prods.map((item) => [item.id, item])).values());
        setProducts(unique);
      }
    } catch (e) {
      console.error("Failed to load products for gallery upload", e);
    }
  };

  useEffect(() => {
    fetchGallery();
    fetchProducts();
  }, [categoryFilter]);

  // Handle local file selection with preview
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!["image/jpeg", "image/png", "image/webp", "image/jpg"].includes(file.type)) {
      setUploadError(isNepali ? "JPEG, PNG वा WEBP फाइल मात्र समर्थित छ" : "Allowed formats: JPEG, PNG, WEBP.");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setUploadError(isNepali ? "फाइल ५ MB भन्दा सानो हुनुपर्छ" : "File must be under 5 MB.");
      return;
    }

    setUploadError(null);
    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setFilePreviewUrl(objectUrl);
  };

  // Submit Photo Upload
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isViewer || !uploadProductId || !selectedFile) return;

    setUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch(`/api/v1/gallery/upload/${uploadProductId}`, {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Upload failed");
      }

      setShowUploadModal(false);
      setSelectedFile(null);
      setFilePreviewUrl(null);
      setUploadProductId("");
      fetchGallery();
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload image");
    } finally {
      setUploading(false);
    }
  };

  // Download Image File
  const handleDownload = async (item: GalleryItem) => {
    try {
      const res = await fetch(`/api/v1/gallery/images/${item.id}/download`);
      if (!res.ok) throw new Error("Failed to download image");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${item.product_code}_${item.file_name}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e: any) {
      alert(e.message || "Download error");
    }
  };

  // Delete Image (Editor only)
  const handleDelete = async (item: GalleryItem) => {
    if (isViewer) return;
    const confirmMsg = isNepali
      ? `के तपाईं ${item.product_code} को फोटो मेटाउन चाहनुहुन्छ?`
      : `Are you sure you want to delete this photo for ${item.product_code}?`;
    if (!window.confirm(confirmMsg)) return;

    try {
      const res = await fetch(`/api/v1/gallery/${item.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Delete failed");
      fetchGallery();
    } catch (e: any) {
      alert(e.message || "Failed to delete image");
    }
  };

  // Filtered items based on search
  const filteredItems = items.filter((it) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      it.product_code.toLowerCase().includes(term) ||
      it.product_name.toLowerCase().includes(term) ||
      (it.category && it.category.toLowerCase().includes(term))
    );
  });

  return (
    <div style={{ padding: "24px 32px", maxWidth: "1600px", margin: "0 auto" }}>
      {/* Top Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
              {t("gallery_title")}
            </h1>
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                background: "#E0E7FF",
                color: "#1E3A8A",
                padding: "2px 8px",
                borderRadius: "3px"
              }}
            >
              {isNepali ? "जुत्ता फोटो क्याटलग" : "SKU MEDIA GALLERY"}
            </span>
          </div>
          <p style={{ fontSize: "12.5px", color: "#475569", marginTop: "4px", margin: 0 }}>
            {t("gallery_desc")}
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={fetchGallery}
            disabled={loading}
            className="pagination-btn"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
            title="Refresh Gallery"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>{isNepali ? "ताजा गर्नुहोस्" : "Refresh"}</span>
          </button>

          {!isViewer && (
            <button
              onClick={() => {
                setUploadError(null);
                setSelectedFile(null);
                setFilePreviewUrl(null);
                setShowUploadModal(true);
              }}
              style={{
                background: "#1E3A8A",
                color: "#FFFFFF",
                border: "none",
                padding: "6px 14px",
                borderRadius: "4px",
                fontSize: "12.5px",
                fontWeight: "600",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              <Upload size={14} />
              <span>{t("upload_photo")}</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div
        style={{
          background: "#FFFFFF",
          border: "1px solid #E2E8F0",
          borderRadius: "6px",
          padding: "12px 16px",
          marginBottom: "20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "12px", color: "#64748B", fontWeight: "500" }}>Category:</span>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              style={{
                padding: "5px 10px",
                fontSize: "12px",
                borderRadius: "4px",
                border: "1px solid #CBD5E1",
                background: "#FFFFFF",
                color: "#0F172A",
                outline: "none"
              }}
            >
              <option value="ALL">{t("all_categories")}</option>
              <option value="Boot">Boot</option>
              <option value="Shoe">Shoe</option>
              <option value="Slipper">Slipper</option>
              <option value="Sandal">Sandal</option>
            </select>
          </div>
        </div>

        {/* Search */}
        <div style={{ position: "relative", minWidth: "280px" }}>
          <Search size={14} color="#94A3B8" style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
          <input
            type="text"
            placeholder={isNepali ? "मोडल नाम वा कोड खोज्नुहोस्..." : "Search product code or name..."}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 10px 6px 32px",
              fontSize: "12.5px",
              border: "1px solid #CBD5E1",
              borderRadius: "4px",
              outline: "none",
              color: "#0F172A"
            }}
          />
        </div>
      </div>

      {/* Error Notice */}
      {error && (
        <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "10px 14px", borderRadius: "6px", color: "#B91C1C", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Visual Product Grid */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "60px", color: "#64748B" }}>
          <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 12px" }} />
          <div>Loading high-resolution product media catalog...</div>
        </div>
      ) : filteredItems.length === 0 ? (
        <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "8px", padding: "60px 20px", textAlign: "center", color: "#64748B" }}>
          <ImageIcon size={40} style={{ margin: "0 auto 12px", opacity: 0.4 }} />
          <div style={{ fontSize: "15px", fontWeight: "600", color: "#0F172A" }}>
            {isNepali ? "ग्यालरीमा कुनै तस्बिर भेटिएन" : "No product images in gallery"}
          </div>
          <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
            {isViewer
              ? "No photos have been uploaded by factory supervisors yet."
              : "Click '+ Upload Photo' to attach high-resolution shoe photos to any footwear SKU."}
          </p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "18px" }}>
          {filteredItems.map((item) => (
            <div
              key={item.id}
              style={{
                background: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "8px",
                overflow: "hidden",
                boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                display: "flex",
                flexDirection: "column",
                transition: "transform 0.15s ease, box-shadow 0.15s ease"
              }}
            >
              {/* Product Photo Container */}
              <div
                style={{
                  position: "relative",
                  width: "100%",
                  height: "220px",
                  background: "#F1F5F9",
                  overflow: "hidden",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center"
                }}
                onClick={() => setPreviewImageModal(item)}
              >
                <img
                  src={`/api/v1/gallery/images/${item.id}/download`}
                  alt={item.product_name}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover"
                  }}
                  onError={(e) => {
                    (e.target as any).style.display = "none";
                  }}
                />

                {/* Category Badge overlay */}
                {item.category && (
                  <span
                    style={{
                      position: "absolute",
                      top: "10px",
                      left: "10px",
                      background: "rgba(15, 23, 42, 0.75)",
                      color: "#FFFFFF",
                      fontSize: "10.5px",
                      fontWeight: "700",
                      padding: "3px 8px",
                      borderRadius: "3px",
                      backdropFilter: "blur(2px)"
                    }}
                  >
                    {item.category}
                  </span>
                )}

                {/* Zoom Hint */}
                <div
                  style={{
                    position: "absolute",
                    bottom: "8px",
                    right: "8px",
                    background: "rgba(255, 255, 255, 0.85)",
                    borderRadius: "4px",
                    padding: "4px 6px",
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                    fontSize: "11px",
                    color: "#0F172A"
                  }}
                >
                  <Eye size={12} />
                  <span>Preview</span>
                </div>
              </div>

              {/* Card Meta Content */}
              <div style={{ padding: "14px 16px", flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontSize: "12px", fontWeight: "700", color: "#1E3A8A", fontFamily: "'Fira Code', monospace" }}>
                      {item.product_code}
                    </span>
                    <span style={{ fontSize: "11px", color: "#64748B" }}>
                      {item.file_size_bytes ? `${Math.round(item.file_size_bytes / 1024)} KB` : ""}
                    </span>
                  </div>

                  <h3 style={{ fontSize: "14px", fontWeight: "600", color: "#0F172A", margin: "0 0 8px 0", lineHeight: "1.3" }}>
                    {item.product_name}
                  </h3>
                </div>

                {/* Action Buttons */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #F1F5F9", paddingTop: "10px", marginTop: "10px" }}>
                  <button
                    onClick={() => handleDownload(item)}
                    style={{
                      background: "#F8FAFC",
                      border: "1px solid #CBD5E1",
                      borderRadius: "4px",
                      padding: "5px 10px",
                      fontSize: "11.5px",
                      fontWeight: "600",
                      color: "#1E293B",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "5px"
                    }}
                    title="Download Photo for Wholesale Order Sheet"
                  >
                    <Download size={12} />
                    <span>{t("download_image")}</span>
                  </button>

                  {!isViewer && (
                    <button
                      onClick={() => handleDelete(item)}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "#DC2626",
                        cursor: "pointer",
                        padding: "4px 6px",
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        fontSize: "11px"
                      }}
                      title="Delete Image"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* MODAL 1: UPLOAD PHOTO */}
      {showUploadModal && !isViewer && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px"
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              borderRadius: "8px",
              width: "100%",
              maxWidth: "520px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
              overflow: "hidden"
            }}
          >
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Upload size={18} color="#1E3A8A" />
                <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                  {t("upload_photo")}
                </h3>
              </div>
              <button onClick={() => setShowUploadModal(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} style={{ padding: "20px" }}>
              {uploadError && (
                <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "8px 12px", borderRadius: "4px", color: "#B91C1C", marginBottom: "14px", fontSize: "12.5px" }}>
                  {uploadError}
                </div>
              )}

              {/* Select Product */}
              <div style={{ marginBottom: "14px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Select Footwear SKU *
                </label>
                <select
                  required
                  value={uploadProductId}
                  onChange={(e) => setUploadProductId(Number(e.target.value))}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    fontSize: "12.5px",
                    border: "1px solid #CBD5E1",
                    borderRadius: "4px",
                    background: "#FFFFFF",
                    outline: "none"
                  }}
                >
                  <option value="">-- Choose Footwear SKU / Model --</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.code} - {p.name} {p.category ? `(${p.category})` : ""}
                    </option>
                  ))}
                </select>
              </div>

              {/* File Upload Box */}
              <div style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Image File (JPEG, PNG, WEBP &le; 5 MB) *
                </label>
                <div
                  style={{
                    border: "2px dashed #CBD5E1",
                    borderRadius: "6px",
                    padding: "20px",
                    textAlign: "center",
                    background: "#F8FAFC",
                    cursor: "pointer"
                  }}
                  onClick={() => document.getElementById("galleryFileInput")?.click()}
                >
                  {filePreviewUrl ? (
                    <div>
                      <img
                        src={filePreviewUrl}
                        alt="Preview"
                        style={{ maxHeight: "150px", margin: "0 auto 8px", borderRadius: "4px", objectFit: "contain" }}
                      />
                      <div style={{ fontSize: "12px", color: "#0F172A", fontWeight: "600" }}>{selectedFile?.name}</div>
                      <div style={{ fontSize: "11px", color: "#64748B" }}>Click to replace file</div>
                    </div>
                  ) : (
                    <div>
                      <ImageIcon size={32} color="#94A3B8" style={{ margin: "0 auto 8px" }} />
                      <div style={{ fontSize: "13px", fontWeight: "600", color: "#0F172A" }}>
                        Click to select photo from computer
                      </div>
                      <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
                        High-resolution industrial product photos (JPEG, PNG, WEBP)
                      </div>
                    </div>
                  )}
                  <input
                    id="galleryFileInput"
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/jpg"
                    style={{ display: "none" }}
                    onChange={handleFileChange}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  style={{ padding: "7px 14px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", color: "#475569", fontSize: "12.5px", cursor: "pointer" }}
                >
                  {t("close")}
                </button>
                <button
                  type="submit"
                  disabled={uploading || !selectedFile || !uploadProductId}
                  style={{
                    padding: "7px 18px",
                    border: "none",
                    borderRadius: "4px",
                    background: "#1E3A8A",
                    color: "#FFFFFF",
                    fontSize: "12.5px",
                    fontWeight: "600",
                    cursor: "pointer",
                    opacity: uploading || !selectedFile || !uploadProductId ? 0.6 : 1
                  }}
                >
                  {uploading ? "Uploading..." : t("commit_record")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: FULLSCREEN IMAGE PREVIEW */}
      {previewImageModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.85)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1100,
            padding: "24px"
          }}
          onClick={() => setPreviewImageModal(null)}
        >
          <div
            style={{
              position: "relative",
              maxWidth: "900px",
              width: "100%",
              maxHeight: "90vh",
              display: "flex",
              flexDirection: "column",
              background: "#0F172A",
              borderRadius: "8px",
              overflow: "hidden"
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ padding: "12px 18px", background: "rgba(0,0,0,0.4)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ color: "#FFFFFF" }}>
                <span style={{ fontWeight: "700", fontSize: "14px", fontFamily: "'Fira Code', monospace", color: "#93C5FD", marginRight: "10px" }}>
                  {previewImageModal.product_code}
                </span>
                <span style={{ fontSize: "13px" }}>{previewImageModal.product_name}</span>
              </div>
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  onClick={() => handleDownload(previewImageModal)}
                  style={{ background: "#1E3A8A", border: "none", color: "#FFFFFF", padding: "4px 10px", borderRadius: "4px", fontSize: "12px", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px" }}
                >
                  <Download size={13} />
                  <span>Download</span>
                </button>
                <button
                  onClick={() => setPreviewImageModal(null)}
                  style={{ background: "none", border: "none", color: "#94A3B8", cursor: "pointer" }}
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* Photo View */}
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "10px", maxHeight: "75vh" }}>
              <img
                src={`/api/v1/gallery/images/${previewImageModal.id}/download`}
                alt={previewImageModal.product_name}
                style={{ maxWidth: "100%", maxHeight: "70vh", objectFit: "contain" }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
