import { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorState } from "@/components/shared/ErrorState";

interface RootErrorBoundaryProps {
  children: ReactNode;
}

interface RootErrorBoundaryState {
  hasError: boolean;
}

/** Root-level error boundary with a reload action (docs/architecture/07). */
export class RootErrorBoundary extends Component<
  RootErrorBoundaryProps,
  RootErrorBoundaryState
> {
  state: RootErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): RootErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Logging pipeline lands with the logging prompt.
    console.error("RootErrorBoundary caught", error, info);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="container px-4 py-10">
          <ErrorState
            message="An unexpected error occurred."
            onRetry={() => this.setState({ hasError: false })}
          />
        </div>
      );
    }
    return this.props.children;
  }
}
