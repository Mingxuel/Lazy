using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Input;
using System.Windows.Markup;

namespace MarcoMVVM
{
    public class RelayCommand : ICommand
    {
        /* =======================================================================================
        public interface ICommand
        {
            event EventHandler? CanExecuteChanged;
            bool CanExecute(object? parameter);
            void Execute(object? parameter);
        }
        ========================================================================================*/

        private readonly Action<object> _execute;   //没有返回值的委托
        private readonly Func<object, bool> _canExecute;    //返回bool值的委托, Func就是委托方法

        public RelayCommand(Action<object> execute) : this(execute, null)
        {

        }

        public RelayCommand(Action<object> execute, Func<object, bool> canExecute)
        {
            _execute = execute;
            _canExecute = canExecute;
        }

        public bool CanExecute(object parameter)
        {
            //如果_canExecute为null, 则直接返回null, 不会引发NullReferenceException.
            //Invoke指的是调用该委托方法
            //在这里, 如果_canExecute?.Invoke()返回null, 则返回true.
            return _canExecute?.Invoke(parameter) ?? true;
            //return _canExecute == null || _canExecute(parameter);
        }

        public void Execute(object parameter) => _execute(parameter);

        public event EventHandler CanExecuteChanged
        {
            add => CommandManager.RequerySuggested += value;
            remove => CommandManager.RequerySuggested -= value;
        }
    }
}
