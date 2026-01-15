using CommunityToolkit.Mvvm.ComponentModel;
using System;
using System.Collections.Generic;
using System.Configuration;
using System.Linq;
using System.Text;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace MarcoMVVM
{
    public partial class User : ObservableObject
    {
        [ObservableProperty]
        [property: JsonPropertyName("FullName")]
        public string name;

        [ObservableProperty]
        public string age;

        [ObservableProperty]
        [property: JsonIgnore]
        public string password;
    }

    [ObservableObject]
    public partial class Customer
    {
        public string Name { get; set; }
        public string Age { get; set; }
        public string Password { get; set; }
    }

    [INotifyPropertyChanged]
    public partial class Owner
    {
        public string Name { get; set; }
        public string Age { get; set; }
        public string Password { get; set; }
    }

    public class OriginOwner
    {
        public string Name { get; set; }
        public string Age { get; set; }
        public string Password { get; set; }
    }

    //通用类转MVVM类
    public partial class ObservableOwner :ObservableObject
    {
        private readonly OriginOwner originOwner;

        public ObservableOwner(OriginOwner originOwner)
        {
            this.originOwner = originOwner;
        }
        public string Name 
        { 
            get => originOwner.Name;
            set => SetProperty(originOwner.Name, value, originOwner, (originOwner, name) => originOwner.Name = name);
        }

        public string Age
        {
            get => originOwner.Age;
            set => SetProperty(originOwner.Age, value, originOwner, (originOwner, age) => originOwner.Age = age);
        }

        public string Password
        {
            get => originOwner.Password;
            set => SetProperty(originOwner.Password, value, originOwner, (originOwner, password) => originOwner.Password = password);
        }
    }
}
