import argparse
from config import Config
from database import init_database
from stage1_collector import CandleCollector
from stage2_filter import TripleRSIFilter
from stage3_gpt_decision import GPTDecision
from stage4_execution import PaperExecutor
from stage5_labeling import Labeler
from stage6_optimization import Optimizer
from stage7_backtest import WalkForwardBacktester
from stage8_orchestrator import Orchestrator
from stage9_control import Controller

def cmd_collect(args):
    Session = init_database(Config.DATABASE_URL)
    session = Session()
    c = CandleCollector(session)
    saved = c.collect_historical(days=args.days, symbols=args.symbols, timeframes=args.timeframes)
    print(f"saved {saved} candles.")

def cmd_filter(args):
    Session = init_database(Config.DATABASE_URL)
    session = Session()
    f = TripleRSIFilter(session)
    total = 0
    for s in args.symbols:
        for tf in args.timeframes:
            made = f.scan(s, tf)
            print(f"{s} {tf}: candidates {made}")
            total += made
    print(f"total candidates: {total}")

def cmd_gpt_score(args):
    Session = init_database(Config.DATABASE_URL)
    session = Session()
    g = GPTDecision(session)
    if args.model in ('gpt-3.5', 'gpt-4.0'):
        Config.GPT_MODEL_KEY = args.model
    if args.provider in ('openai', 'anthropic'):
        Config.GPT_PROVIDER = args.provider
    n = g.score_all_unscored(provider=Config.GPT_PROVIDER, model_key=Config.GPT_MODEL_KEY)
    print(f"scored {n} candidates with {Config.GPT_PROVIDER}/{Config.resolve_model()}")

def cmd_set_model(args):
    if args.model:
        Config.GPT_MODEL_KEY = args.model
    if args.provider:
        Config.GPT_PROVIDER = args.provider
    print(f"set GPT to {Config.GPT_PROVIDER}/{Config.resolve_model()}")

def cmd_execute(args):
    Session = init_database(Config.DATABASE_URL)
    session = Session()
    ex = PaperExecutor(session)
    total = ex.execute_new_trades(symbols=args.symbols, timeframes=args.timeframes)
    print(f"executed {total} new paper trades.")

def cmd_label(args):
    Session = init_database(Config.DATABASE_URL)
    session = Session()
    lab = Labeler(session)
    made = lab.label_unlabeled()
    print(f"created {made} new labels.")

def cmd_optimize(args):
    Session = init_database(Config.DATABASE_URL)
    session = Session()
    opt = Optimizer(session)
    rep = opt.optimize(train_days=args.train_days,
                       test_days=args.test_days,
                       symbols=args.symbols,
                       timeframes=args.timeframes,
                       approve=args.approve)
    print("OptimizationReport:", {
        "id": rep.id,
        "stat_sig": rep.statistical_significance,
        "approved": rep.approved,
        "old_train": rep.old_results.get("train") if rep.old_results else None,
        "new_train": rep.new_results.get("train") if rep.new_results else None,
        "old_test": rep.old_results.get("test") if rep.old_results else None,
        "new_test": rep.new_results.get("test") if rep.new_results else None,
    })

def cmd_approve(args):
    Session = init_database(Config.DATABASE_URL)
    session = Session()
    opt = Optimizer(session)
    rep = opt.approve_report(report_id=args.report_id, approve=args.approve, reason=args.reason)
    print(f"Report {rep.id} approved={rep.approved} by {rep.approved_by}. Filters {'activated' if rep.approved else 'unchanged'}.")

def cmd_backtest(args):
    Session = init_database(Config.DATABASE_URL)
    session = Session()
    bt = WalkForwardBacktester(session)
    res = bt.run(train_days=args.train_days, test_days=args.test_days, steps=args.steps,
                 symbols=args.symbols, timeframes=args.timeframes, filt_cfg=Config.FILTERS)
    print("Backtest summary:", {k: v for k, v in res.items() if k != 'detail'})
    # If you want details:
    # import json; print(json.dumps(res, default=str, indent=2))

def cmd_control(args):
    Session = init_database(Config.DATABASE_URL)
    session = Session()
    ctl = Controller(session)
    res = ctl.handle(args.command)
    import json; print(json.dumps(res, default=str, indent=2))

def cmd_orchestrate(args):
    Session = init_database(Config.DATABASE_URL)
    session = Session()
    orch = Orchestrator(session)
    orch.run_once(days=args.days,
                  symbols=args.symbols,
                  timeframes=args.timeframes,
                  provider=args.provider,
                  model_key=args.model)

def parse_sym_tf(v):
    return [x.strip() for x in v.split(',') if x.strip()]

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    c = sub.add_parser('collect')
    c.add_argument('--days', type=int, default=3)
    c.add_argument('--symbols', type=parse_sym_tf, default="ES,NQ,YM")
    c.add_argument('--timeframes', type=parse_sym_tf, default="1m,5m,15m")
    c.set_defaults(func=cmd_collect)

    f = sub.add_parser('filter')
    f.add_argument('--symbols', type=parse_sym_tf, default="ES")
    f.add_argument('--timeframes', type=parse_sym_tf, default="5m")
    f.set_defaults(func=cmd_filter)

    g = sub.add_parser('gpt-score')
    g.add_argument('--provider', choices=['openai','anthropic'], default=Config.GPT_PROVIDER)
    g.add_argument('--model', choices=['gpt-3.5','gpt-4.0'], default=Config.GPT_MODEL_KEY)
    g.set_defaults(func=cmd_gpt_score)

    s = sub.add_parser('set-model')
    s.add_argument('--provider', choices=['openai','anthropic'], required=False)
    s.add_argument('--model', choices=['gpt-3.5','gpt-4.0'], required=False)
    s.set_defaults(func=cmd_set_model)

    e = sub.add_parser('execute')
    e.add_argument('--symbols', type=parse_sym_tf, default="ES")
    e.add_argument('--timeframes', type=parse_sym_tf, default="5m")
    e.set_defaults(func=cmd_execute)

    l = sub.add_parser('label')
    l.set_defaults(func=cmd_label)

    o = sub.add_parser('optimize')
    o.add_argument('--train-days', type=int, default=Config.WALK_FORWARD_TRAIN_DAYS)
    o.add_argument('--test-days', type=int, default=Config.WALK_FORWARD_TEST_DAYS)
    o.add_argument('--approve', action='store_true', help='Auto-approve if improved')
    o.add_argument('--symbols', type=parse_sym_tf, default="ES")
    o.add_argument('--timeframes', type=parse_sym_tf, default="5m")
    o.set_defaults(func=cmd_optimize)

    a = sub.add_parser('approve')
    a.add_argument('--report-id', type=int, required=True)
    a.add_argument('--approve', action='store_true')
    a.add_argument('--reason', type=str, default="")
    a.set_defaults(func=cmd_approve)

    b = sub.add_parser('backtest')
    b.add_argument('--train-days', type=int, default=Config.WALK_FORWARD_TRAIN_DAYS)
    b.add_argument('--test-days', type=int, default=Config.WALK_FORWARD_TEST_DAYS)
    b.add_argument('--steps', type=int, default=2)
    b.add_argument('--symbols', type=parse_sym_tf, default="ES")
    b.add_argument('--timeframes', type=parse_sym_tf, default="5m")
    b.set_defaults(func=cmd_backtest)

    ctrl = sub.add_parser('control')
    ctrl.add_argument('command', type=str, help='Natural language command in quotes')
    ctrl.set_defaults(func=cmd_control)

    r = sub.add_parser('orchestrate')
    r.add_argument('--days', type=int, default=0, help='Collect this many historical days first (0=skip)')
    r.add_argument('--symbols', type=parse_sym_tf, default="ES")
    r.add_argument('--timeframes', type=parse_sym_tf, default="5m")
    r.add_argument('--provider', choices=['openai','anthropic'], default=Config.GPT_PROVIDER)
    r.add_argument('--model', choices=['gpt-3.5','gpt-4.0'], default=Config.GPT_MODEL_KEY)
    r.set_defaults(func=cmd_orchestrate)

    args = ap.parse_args()
    # normalize comma inputs
    if hasattr(args, 'symbols') and isinstance(args.symbols, str):
        args.symbols = parse_sym_tf(args.symbols)
    if hasattr(args, 'timeframes') and isinstance(args.timeframes, str):
        args.timeframes = parse_sym_tf(args.timeframes)
    args.func(args)

if __name__ == "__main__":
    main()
