import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import useAppStore from './store/useAppStore'
import LoginPage from './pages/LoginPage'
import FieldsPage from './pages/FieldsPage'
import FlightPage from './pages/FlightPage'
import UsersPage from './pages/UsersPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAppStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <FieldsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/flights/:flightId"
          element={
            <ProtectedRoute>
              <FlightPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/users"
          element={
            <ProtectedRoute>
              <UsersPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
