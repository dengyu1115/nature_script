data.module = "etf_item";
data.status_map = data.status_options.reduce((map, item) => {
  if (!map[item.value]) {
    map[item.value] = item.label;
  }
  return map;
}, {});
data.type_map = data.type_options.reduce((map, item) => {
  if (!map[item.value]) {
    map[item.value] = item.label;
  }
  return map;
}, {});
data.init_datum = (item) => {
  data.datum = {};
  Object.keys(item).forEach((i) => {
    data.datum[i] = item[i];
  });
};
data.refresh = () => {
  data.list = invoke("python", {
    module: "etf_item",
    func: "list_all",
    args: {},
  });
  data.count = data.list.length;
};
data.refresh();