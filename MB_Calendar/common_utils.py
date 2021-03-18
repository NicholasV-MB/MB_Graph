import os

# GLOBAL VAR OF LAT&LONG of ModulBlok Headquarter
MB_HEADQUARTER_LATITUDE = 46.117620
MB_HEADQUARTER_LONGITUDE = 13.194870



def remove_all_files_inside_folder(path):
    """
    Method to delete all files inside folder
    @param path to folder
    """
    onlyfiles = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    for el in onlyfiles:
        os.remove(path+el)
