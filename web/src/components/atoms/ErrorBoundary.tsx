import { Component, type ErrorInfo, type ReactNode } from 'react';
import Card from './Card';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '100%', 
          padding: '2rem' 
        }}>
          <Card className="error-card">
            <div style={{ textAlign: 'center' }}>
              <AlertTriangle size={48} color="var(--color-error)" style={{ marginBottom: '1rem' }} />
              <h2 style={{ color: 'var(--color-primary)', marginBottom: '1rem' }}>Something went wrong</h2>
              <p style={{ color: 'var(--color-text-secondary)', marginBottom: '2rem' }}>
                The application encountered an unexpected error. Our candidate records are safe, but the current view crashed.
              </p>
              <button 
                onClick={() => window.location.reload()}
                style={{
                  backgroundColor: 'var(--color-primary)',
                  color: 'var(--color-text-inverse)',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: 'var(--border-radius-md)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  margin: '0 auto',
                  cursor: 'pointer'
                }}
              >
                <RotateCcw size={18} />
                Reload Application
              </button>
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
