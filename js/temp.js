location.href =
  "index.html?id=fund_profit_chart&" +
  new URLSearchParams({
    code: data.rule.code,
    rule: data.rule.name,
  }).toString();
