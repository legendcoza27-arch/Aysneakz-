import { Outlet, Link } from 'react-router-dom';
import { useCartStore } from '../store/cartStore';

export default function Layout() {
  const count = useCartStore(state => state.count());

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b px-6 py-4 flex justify-between items-center">
        <Link to="/" className="text-xl font-bold">Aysneakz</Link>
        <nav className="flex gap-4">
          <Link to="/catalog">Shop</Link>
          <Link to="/cart" className="relative">
            Cart ({count})
          </Link>
          <Link to="/orders">Orders</Link>
        </nav>
      </header>
      <main className="flex-1 px-6 py-8 max-w-7xl mx-auto w-full">
        <Outlet />
      </main>
      <footer className="bg-gray-50 text-center py-6 text-sm text-gray-500">
        © {new Date().getFullYear()} Aysneakz
      </footer>
    </div>
  );
}