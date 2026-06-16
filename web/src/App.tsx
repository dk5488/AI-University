import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Shell from './components/templates/Shell';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage';
import QuizPage from './pages/QuizPage';
import './styles/variables.css';

import ErrorBoundary from './components/atoms/ErrorBoundary';
import { ToastProvider } from './hooks/ToastContext';

const queryClient = new QueryClient();

function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <Shell>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/quiz/:subjectCode/:topicSlug" element={<QuizPage />} />
                <Route path="/revisions" element={<div>Revisions (Coming Soon)</div>} />
              </Routes>
            </Shell>
          </BrowserRouter>
        </QueryClientProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;
