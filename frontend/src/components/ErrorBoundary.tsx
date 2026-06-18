import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="card panel" style={{ textAlign: "center", padding: "2rem" }}>
          <h2>Something went wrong</h2>
          <p className="muted">{this.state.error?.message ?? "An unexpected error occurred."}</p>
          <button onClick={() => window.location.reload()}>Reload Page</button>
        </section>
      );
    }
    return this.props.children;
  }
}
