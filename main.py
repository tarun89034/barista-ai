"""
Main entry point for Barista AI Portfolio Management System.

Usage:
    # Start the API server
    python main.py serve
    python main.py serve --host 0.0.0.0 --port 8000

    # CLI commands
    python main.py analyze --file data/sample_portfolio.csv --period 1y
    python main.py risk --file data/sample_portfolio.csv --period 1y
    python main.py monitor --file data/sample_portfolio.csv
    python main.py rebalance --file data/sample_portfolio.csv --profile moderate
"""

import argparse
import sys
import json
import logging

from src.utils.logger import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="Barista AI - Portfolio Risk Management & Advisor Agent"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Serve command (API server)
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # Analyze command (full analysis)
    analyze_parser = subparsers.add_parser("analyze", help="Run full portfolio analysis")
    analyze_parser.add_argument("--file", required=True, help="Path to portfolio CSV/Excel file")
    analyze_parser.add_argument("--period", default="1y", help="Analysis period (default: 1y)")
    analyze_parser.add_argument("--profile", default="moderate",
                                choices=["conservative", "moderate", "aggressive"],
                                help="Risk profile for rebalancing")

    # Risk command
    risk_parser = subparsers.add_parser("risk", help="Run risk analysis only")
    risk_parser.add_argument("--file", required=True, help="Path to portfolio file")
    risk_parser.add_argument("--period", default="1y", help="Analysis period (default: 1y)")

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor portfolio market data")
    monitor_parser.add_argument("--file", required=True, help="Path to portfolio file")

    # Rebalance command
    rebalance_parser = subparsers.add_parser("rebalance", help="Get rebalancing recommendations")
    rebalance_parser.add_argument("--file", required=True, help="Path to portfolio file")
    rebalance_parser.add_argument("--profile", default="moderate",
                                   choices=["conservative", "moderate", "aggressive"],
                                   help="Risk profile")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    setup_logging(log_level="INFO")

    if args.command == "serve":
        _run_server(args)
    else:
        _run_cli(args)


def _run_server(args):
    """Start the FastAPI server."""
    try:
        import uvicorn
        from src.api.app import create_app

        app = create_app()
        print(f"\n  Barista AI API Server")
        print(f"  Listening on http://{args.host}:{args.port}")
        print(f"  API docs:   http://{args.host}:{args.port}/docs")
        print()

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info",
        )
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install uvicorn[standard]", file=sys.stderr)
        sys.exit(1)


def _run_cli(args):
    """Execute CLI commands."""
    from src.agents.portfolio_reader import PortfolioReaderAgent
    from src.agents.risk_analyzer import RiskAnalyzerAgent
    from src.agents.market_monitor import MarketMonitorAgent
    from src.agents.rebalancing_advisor import RebalancingAdvisorAgent

    try:
        if args.command == "analyze":
            reader = PortfolioReaderAgent()
            portfolio = reader.process(args.file)
            print(f"\nPortfolio loaded: {portfolio.name} ({len(portfolio.assets)} assets)")

            analyzer = RiskAnalyzerAgent()
            risk_results = analyzer.process(portfolio, period=args.period)
            print(f"\nRisk Analysis Complete:")
            print(json.dumps(risk_results.get("risk_summary", {}), indent=2))

            monitor = MarketMonitorAgent()
            monitoring = monitor.process(portfolio)
            print(f"\nMarket Monitoring: {monitoring.get('alert_count', 0)} alerts")

            advisor = RebalancingAdvisorAgent(risk_profile=args.profile)
            rebalancing = advisor.process(portfolio, risk_analysis=risk_results)
            print(f"\nRebalancing needed: {rebalancing.get('needs_rebalancing', False)}")
            if rebalancing.get("recommendations"):
                print("Recommendations:")
                for rec in rebalancing["recommendations"]:
                    print(f"  {rec['action']} {rec['asset_type']}: {rec['reason']}")

        elif args.command == "risk":
            reader = PortfolioReaderAgent()
            portfolio = reader.process(args.file)
            analyzer = RiskAnalyzerAgent()
            results = analyzer.process(portfolio, period=args.period)
            print(json.dumps(results, indent=2, default=str))

        elif args.command == "monitor":
            reader = PortfolioReaderAgent()
            portfolio = reader.process(args.file)
            monitor = MarketMonitorAgent()
            results = monitor.process(portfolio)
            print(json.dumps(results, indent=2, default=str))

        elif args.command == "rebalance":
            reader = PortfolioReaderAgent()
            portfolio = reader.process(args.file)
            advisor = RebalancingAdvisorAgent(risk_profile=args.profile)
            results = advisor.process(portfolio)
            print(json.dumps(results, indent=2, default=str))

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        logging.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
