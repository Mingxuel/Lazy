namespace MyDream
{
    public class ZZ500Item
    {
        public string? StockCode { get; set; }
        public string? StockName { get; set; }
        public string? Industry { get; set; }
        public List<string>? Concepts { get; set; }
        public double? Volume { get; set; }

        public ZZ500Item() { }

        public ZZ500Item(string data_string)
        {
            var data = data_string.Split("|").ToList();
            StockCode = data[0];
            StockName = data[1];
            Industry = data[2];
            Concepts = data[3].Split(";").ToList();
            Volume = double.Parse(data[4]);
        }

        public override string ToString()
        {
            return $"{StockCode}|{StockName}|{Industry}|{string.Join(";", Concepts!)}|{Volume}";
        }
    }
}
