Installation is same as containR  

### Compared to the previous version:  

The build_image_py.py is renamed as "pyPlace.py" and now it is implementing an interface named "language_interface.py"  

The old build_image_py method is divided into 6 parts: preprocessing,build_docker_file,create_report,build_docker_img,push_docker_img and clean_up_datasets  
preprocessing,build_docker_file,create_report and clean_up_datasets are specificed to language so they are implemented in pyPlace class and the rest of them can be commonly used among different language so they are implemented in the "language_interface.py"
interface.  

The frontend now will call a method called "start_raas" implemented in the "start.py" class, start_raas will:  
1)check the language as input  
2)create the corresponding language object(pyPlace)  
3)it organize the order of the call of those 6 methods   
__________________________________________________
### How to support another language?

1.Create a new object that implement the "language_interface".  
The method you would need to implement are 
  
     preprocessing(self, preprocess, dataverse_key='', doi='', zip_file='', run_instr='', user_pkg='')

     build_docker_file(self, dir_name, docker_pkgs, addtional_info):
       
     create_report(self, current_user_id, name, dir_name)

     clean_up_datasets(self, dir)
2.in the start.py, add an if condition to check the input language name corresponding to your language  
3.do not forget to change the frontend
