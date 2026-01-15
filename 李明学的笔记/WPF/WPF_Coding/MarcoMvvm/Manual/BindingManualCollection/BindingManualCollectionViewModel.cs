using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Input;

namespace MarcoMVVM
{
    internal class BindingManualCollectionViewModel : ViewModelBase
    {
        public ICommand DeleteItemCommand { get; set; }

        public BindingManualCollectionView.UserData _selectedItem;
        public BindingManualCollectionView.UserData SelectedItem
        {
            get { return _selectedItem; }
            set
            {
                _selectedItem = value;
                OnPropertyChanged();
            }
        }

        public BindingManualCollectionViewModel()
        {
            DeleteItemCommand = new RelayCommand(param => DeleteItem());
        }

        public ObservableCollection<BindingManualCollectionView.UserData> ListViewData { get; set; } = new ObservableCollection<BindingManualCollectionView.UserData>()
        {
            new BindingManualCollectionView.UserData(){ID = "1", NAME = "MARCO", PASSWORD = "11" },
            new BindingManualCollectionView.UserData(){ID = "2", NAME = "JENNY", PASSWORD = "22" },
            new BindingManualCollectionView.UserData(){ID = "3", NAME = "MAX", PASSWORD = "33" },
            new BindingManualCollectionView.UserData(){ID = "4", NAME = "NEDVED", PASSWORD = "44" },
            new BindingManualCollectionView.UserData(){ID = "5", NAME = "PUDGE", PASSWORD = "55" },
            new BindingManualCollectionView.UserData(){ID = "6", NAME = "MALVE", PASSWORD = "66" },
        };

        private void DeleteItem()
        {
            ListViewData.Remove(SelectedItem);
        }
    }
}
