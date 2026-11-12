# 16 · Cost calculator

Works out the cost of one model call and of a whole agent run, and shows why the cost of a run grows much faster than its number of steps: the agent resends the whole conversation every step. Used in [16.1 Token cost maths](../../docs/16-cost-and-performance/16.1-token-cost-maths.md).

Claude prices are as of November 2026, from the [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing). Check it before you rely on them. OpenAI prices are not hard-coded: set `OPENAI_INPUT_PRICE` and `OPENAI_OUTPUT_PRICE` (dollars per million tokens) to include a model of yours.

## Run it

```bash
cd examples
python 16-cost-calculator/main.py
```

Output (pure arithmetic, no model calls):

```text
1) One call: 2,000 tokens in, 500 tokens out
   claude-opus-5-5    $0.018000
   claude-sonnet-5-5  $0.009000
   claude-haiku-5-5   $0.000450

2) An agent loop: LoopShape(fixed=3000, goal=100, output=200, tool_result=800)
   steps   input tokens   output tokens   Opus 5.5   Sonnet 5.5   Haiku 5.5
       1          3,100             200     $0.016       $0.008     $0.0004
       5         25,500           1,000     $0.122       $0.061     $0.0031
      10         76,000           2,000     $0.344       $0.172     $0.0086
      20        252,000           4,000     $1.088       $0.544     $0.0272
      40        904,000           8,000     $3.776       $1.888     $0.0944

   Doubling the steps from 10 to 20 multiplies the Opus 5.5 cost by 3.2x, not 2x.

3) Where the 10-step run's input tokens come from
   fixed prefix resent 10 times:  31,000 (41%)
   growing history resent:        45,000 (59%)

4) Set OPENAI_INPUT_PRICE and OPENAI_OUTPUT_PRICE to compare an OpenAI model.
```

## Test it

```bash
pytest 16-cost-calculator
```

The 11 tests check single-call prices, cache pricing, the resending model, that the closed-form formula matches the simulation, the faster-than-linear growth, cost from real usage records, and that OpenAI prices only come from the environment.

## Things to try

- Change `LoopShape` to match your own agent (measure `fixed`, `output` and `tool_result` from your traces).
- Set `tool_result=4000` and see what large tool results do to the bill.
