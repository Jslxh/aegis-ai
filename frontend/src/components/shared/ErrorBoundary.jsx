import React from "react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="max-w-md space-y-4 text-center">
          <div className="text-4xl font-bold text-destructive">Unexpected Error</div>
          <p className="text-sm text-muted-foreground">
            Something went wrong rendering this view. Your data is safe.
          </p>
          <code className="block rounded bg-muted px-3 py-2 text-xs text-muted-foreground">
            {this.state.error?.message || "Unknown error"}
          </code>
          <button
            onClick={this.handleReset}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
          >
            Reload view
          </button>
        </div>
      </div>
    );
  }
}
