import { createBrowserRouter, Navigate } from 'react-router-dom';
import Layout from '../components/Layout';
import Home from '../pages/Home';
import Catalog from '../pages/Catalog';
import Login from '../pages/Login';
import { useAuthStore } from '../store/authStore';

// Placeholder pages (create empty files first)
const Cart = () => <div>Cart</div>;
const Checkout = () => <div>Checkout</div>;
const OrderHistory = () => <div>Orders</div>;

export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

export const router = createBrowserRouter([
  { path: '/', element: <Layout />, children: [
    { index: true, element: <Home /> },
    { path: 'catalog', element: <Catalog /> },
    { path: 'cart', element: <Cart /> },
    { path: 'login', element: <Login /> },
    { path: 'checkout', element: <ProtectedRoute><Checkout /></ProtectedRoute> },
    { path: 'orders', element: <ProtectedRoute><OrderHistory /></ProtectedRoute> },
  ]}
]);