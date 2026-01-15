using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MarcoMVVM.Properties;

namespace MarcoMVVM
{
    public partial class ValidationViewModel : ObservableValidator
    {
        [Required(ErrorMessage = "Username does not empty")]
        [ObservableProperty]
        [MinLength(6, ErrorMessageResourceName = "Username_MinLength", ErrorMessageResourceType =typeof(Lang))]
        [MaxLength(18)]
        private string username = "";

        [Required]
        [ObservableProperty]
        [EmailAddress]
        //[CustomValidation(typeof(ValidationViewModel), nameof(ValidateEmail))]
        private string email = "";

        //public static ValidationResult ValidateEmail(string name, ValidationContext)
        //{

        //}

        //继承ValidationAttribute，写自定义的验证方式，例如CustomValidate
        //[CustomValidate]
        [ObservableProperty]
        [Required]
        [Range(18, 99)]
        private int? age;

        [ObservableProperty]
        private string errorMessages = "";

        partial void OnAgeChanged(int? oldValue, int? newValue)
        {
            //前端实时校验
            ValidateProperty(newValue, nameof(Age));
        }

        [RelayCommand]
        private void Register()
        {
            //后端延时校验
            ValidateAllProperties();

            if (HasErrors)
            {
                ErrorMessages = string.Join(Environment.NewLine, GetErrors());
                //ErrorMessages = string.Join(Environment.NewLine, GetErrors("Username"));
                return;
            }
        }
    }
}
