import { BrowserRouter, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import JobPage from "./pages/JobPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <a href="/" className="app-logo">Caption This</a>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/job/:id" element={<JobPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
