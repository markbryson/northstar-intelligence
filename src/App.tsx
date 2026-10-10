import { Route, Routes } from "react-router-dom";
import { DashboardProvider } from "./context/DashboardContext";
import { AppShell } from "./components/layout/AppShell";
import { OverviewPage } from "./pages/OverviewPage";
import { SalesPage } from "./pages/SalesPage";
import { ProductsPage } from "./pages/ProductsPage";
import { CustomersPage } from "./pages/CustomersPage";
import { GeographyPage } from "./pages/GeographyPage";
import { ReturnsPage } from "./pages/ReturnsPage";

export default function App() {
  return <DashboardProvider><Routes><Route element={<AppShell />}><Route index element={<OverviewPage />} /><Route path="sales" element={<SalesPage />} /><Route path="products" element={<ProductsPage />} /><Route path="customers" element={<CustomersPage />} /><Route path="geography" element={<GeographyPage />} /><Route path="returns" element={<ReturnsPage />} /></Route></Routes></DashboardProvider>;
}
