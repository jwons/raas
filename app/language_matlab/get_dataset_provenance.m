path = fopen('path.txt','rt');
path = fread(path);
path = char(path');
provenance_collector(path)