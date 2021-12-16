import sys, argparse, re, logging, urllib, pandas as pd,  plotly.graph_objects as go, json, os
from pathlib import Path
from Bio import Entrez, SeqIO
from Bio.Seq import Seq
from igraph import Graph, EdgeSeq


class Interface:
    #Finished (unit)
    def __init__(self, alphabet, valid_input_type, accession_pattern):
        self.alphabet = alphabet
        self.valid_input_type = valid_input_type
        self.accession_pattern = accession_pattern
        
    def parse_arguments(self):
        '''Method is used to parse command-line arguments, allowing to interact with the database from script.'''
        parser = argparse.ArgumentParser(description='This script can be used to work with local database of bacterial reference genomes in fasta format.')
        req_arg_grp = parser.add_argument_group('Required arguments')
        arg_dict = {
            "--add-fasta": f"Add new record(s) from locally stored fasta file & metadata file of {self.valid_input_type} format. Expected: file_name.{self.valid_input_type}",
            "--add-ncbi": f"Add new record from NCBI RefSeq database by correct accession number. Expected: valid_accession_number",
            "--add-ncbi-list": f"Add new record(s) from NCBI RefSeq database based on a list of correct accession numbers provided as a file of {self.valid_input_type} format (single column with one header row). Expected: path_to_{self.valid_input_type}",
            "--exp-fasta": f"Create a fasta file containing sequences from local database based on a list of correct accession numbers provided as a file of {self.valid_input_type} format. Expected: path_to_{self.valid_input_type}",
            "--exp-meta": f"Create a csv file containing taxonomic information from local database based on a list of correct accession numbers provided as a file of {self.valid_input_type} format. Expected: path_to_{self.valid_input_type}",
            "--exp-records": f"Create a fasta file containing sequences & a csv file containing taxonomic information from local database based on a list of correct accession numbers provided as a file of {self.valid_input_type} format. Expected: path_to_{self.valid_input_type}",
            "--rm-record": f"Remove records from local database based on a list of correct accession numbers provided as a file of {self.valid_input_type} format. Expected: path_to_{self.valid_input_type}",
            "--ch-header": f"Replace an accession number that exists in local database with user-provided accession number if provided accession number was found in local database. Expected: valid_accession_from_local_db,new_accession",
            "--ch-tax": f"Replace a taxonomy string that exists in local database with user-provided taxonomy string if provided accession number was found in local database. Expected: valid_accession_from_local_db,new_taxonomy_string",
            "--view-data": "Visualize the contents of the local database as a tree chart, showing the number of records that belong to each taxonomic group."
        }

        for arg in arg_dict.keys():
            if arg != "--view-data":
                req_arg_grp.add_argument(arg, metavar='\b', help = arg_dict[arg],required=False)  
            else:
                req_arg_grp.add_argument(arg, help = arg_dict[arg], action='store_true', required=False)

        if len(sys.argv)==1:
            parser.print_help(sys.stderr)
            sys.exit(1)
        self.args = parser.parse_args()
        return self.args

    def check_format(self, raw_accession):
        '''Method checks if provided accession number matches RefSeq accession number conventions.'''
        if re.match(self.accession_pattern, raw_accession): return True
        else: return False

    def check_alphabet(self, raw_sequence):
        '''Method checks if sequence that corresponds to the id contains only allowed characters.'''
        for letter in str(raw_sequence):
            if letter not in self.alphabet:
                return False
        return True

    def check_file_type(self, file_name):
        '''Method checks if provided file type matches allowed file type.'''
        return all([os.path.exists(f'{file_name}.{self.valid_input_type}'), os.path.exists(f'{file_name}.fasta')])

    def read_local(self, file_name):
        '''Method is used to read local sequence and taxonomy information.'''
        local_seq = SeqIO.to_dict(SeqIO.parse(f'{file_name}.fasta', "fasta"))
        local_tax_df = pd.read_csv(f'{file_name}.{self.valid_input_type}', header=[0])
        return local_seq, local_tax_df


class Database:
    #Finished (unit)
    def __init__(self, db_name):
        self.sequence_file = Path(f'{db_name}.fasta')
        self.taxonomy_file = Path(f'{db_name}.csv')
        
    def create_db_files(self):
        '''Method is used to create database file in the directory where the script is.'''
        try:
            self.sequence_file.touch(exist_ok=False)
            self.taxonomy_file.touch(exist_ok=False)
            tax_file_columns = pd.DataFrame(columns=["accession_number","taxonomy_string"])
            tax_file_columns.to_csv(self.taxonomy_file, index=False, header=True)
        except:
            print(f'Current database files: {self.sequence_file}; {self.taxonomy_file}')

    def add_record(self, header, sequence, taxonomy, description):
        '''Method is used to add new record to database files (taxonomy file & fasta file).'''
        new_record_seq = SeqIO.SeqRecord(Seq(sequence),id=header, description=description)
        new_record_tax = pd.DataFrame.from_dict({"accession_number":[header],"taxonomy_string":[taxonomy]})
        with open(self.sequence_file, "a+") as seq_db:
            SeqIO.write(new_record_seq, seq_db, "fasta")
        tax_db = pd.read_csv(self.taxonomy_file, header=[0])
        tax_db = tax_db.append(new_record_tax)
        tax_db.to_csv(self.taxonomy_file, index=False)
        
    def calculate_content(self, taxonomy_string=None):
        '''Method is used to calculate current database content by taxonomic group and store in a file.'''
        try:
            with open(f'adj_set.json', "r+") as f1:
                adj_set = json.load(f1)
            with open(f'count_dict.json', "r+") as f2:
                count_dict = json.load(f2)
            with open(f'encode_dict.json', "r+") as f3:
                encode_dict = json.load(f3)
            adj_set = set(tuple(pair) for pair in adj_set)
            if taxonomy_string:
                taxonomy_list = taxonomy_string.split("|")
                new_adj_dict = {taxonomy_list[i]:taxonomy_list[i+1] for i in range(len(taxonomy_list)-1)}
                for taxon in taxonomy_list:
                    try:
                        count_dict[taxon] += 1
                        encode_dict[taxon]
                    except KeyError:
                        encode_dict[taxon] = max(encode_dict.values()) + 1
                        count_dict[taxon] = 1
                for parent,child in new_adj_dict.items():
                    adj_set.add((encode_dict[parent],encode_dict[child]))
                with open(f'adj_set.json', "w+") as file:
                    json.dump(list(adj_set), file)
                with open(f'count_dict.json', "w+") as file:
                    json.dump(count_dict, file)
                with open(f'encode_dict.json', "w+") as file:
                    json.dump(encode_dict, file)
            return adj_set, count_dict
        except FileNotFoundError:
            tax_db = pd.read_csv(self.taxonomy_file, header=[0])
            split_product = tax_db['taxonomy_string'].str.split("|",expand=True)
            adj_set = set()
            count_dict = {}
            for col in split_product.columns:
                count_dict.update(dict(split_product[col].value_counts()))
            encode_dict = {node:i for i,node in enumerate(count_dict.keys())}
            count_dict = {key:int(value) for key,value in count_dict.items()}
            split_product = split_product.drop_duplicates()
            for i in range(len(split_product.columns)):
                for j in range(len(split_product.iloc[:,i])):
                    if i+1 != len(split_product.columns):
                        adj_set.add((encode_dict[split_product.iloc[j,i]], encode_dict[split_product.iloc[j,i+1]]))
            with open(f'adj_set.json', "w+") as file:
                json.dump(list(adj_set), file)
            with open(f'count_dict.json', "w+") as file:
                json.dump(count_dict, file)
            with open(f'encode_dict.json', "w+") as file:
                json.dump(encode_dict, file)
            return adj_set, count_dict
        

    def find_id(self, valid_accession):
        '''Method is used to check if given id exists in the database.'''
        tax_db = pd.read_csv(self.taxonomy_file, header=[0])
        if valid_accession in list(tax_db["accession_number"]): return True
        else: return False

    def find_tax(self, valid_accession):
        '''Method is used to get taxonomy information of a record in the database.'''
        tax_db = pd.read_csv(self.taxonomy_file, header=[0])
        print(tax_db.index[tax_db["accession_number"] == valid_accession])
        accession_ind = tax_db.index[tax_db["accession_number"] == valid_accession].to_list()[0]
        return tax_db.iloc[accession_ind].loc['taxonomy_string']

    def rm_record(self, valid_accession):
        '''Method is used to remove a record from local database based on accession number.'''
        tax_db = pd.read_csv(self.taxonomy_file, header=[0])
        seq_db = SeqIO.to_dict(SeqIO.parse(self.sequence_file, "fasta"))
        tax_db = tax_db[tax_db["accession_number"] != valid_accession]
        del seq_db[valid_accession]
        with open(self.sequence_file, "w+") as seq_db_file:
            SeqIO.write(seq_db.values(), seq_db_file, "fasta")
        tax_db.to_csv(self.taxonomy_file, index=False)

    def write_tax(self, valid_accession, new_taxonomy):
        '''Method is used to replace a taxonomy information of a record in the database.'''
        tax_db = pd.read_csv(self.taxonomy_file, header=[0])
        accession_ind = tax_db.index[tax_db["accession_number"] == valid_accession].to_list()[0]
        tax_db.at[accession_ind,'taxonomy_string']=new_taxonomy
        tax_db.to_csv(self.taxonomy_file, index=False)

    def write_id(self, old_accession, new_accession):
        '''Method is used to replace an accession of a record in the database.'''
        tax_db = pd.read_csv(self.taxonomy_file, header=[0])
        seq_db = SeqIO.to_dict(SeqIO.parse(self.sequence_file, "fasta"))
        accession_ind = tax_db.index[tax_db["accession_number"] == old_accession].to_list()[0]
        tax_db.at[accession_ind,'accession_number']=new_accession
        seq_db[new_accession] = seq_db[old_accession]
        seq_db[new_accession].id = new_accession
        seq_db[new_accession].description = f'{new_accession} replaced manually'
        del seq_db[old_accession]
        seq_db[new_accession].id = new_accession
        with open(self.sequence_file, "w+") as seq_db_file:
            SeqIO.write(seq_db.values(), seq_db_file, "fasta")
        tax_db.to_csv(self.taxonomy_file, index=False)

    def export_fasta(self, valid_accession):
        '''Method is used to export single sequence in a form of SeqIO record.'''
        seq_db = SeqIO.to_dict(SeqIO.parse(self.sequence_file, "fasta"))
        requested_seq = seq_db[valid_accession]
        return requested_seq
               
    def export_tax(self, valid_accession):
        '''Method is used to export single taxonomy record in a form of numpy.Series'''
        tax_db = pd.read_csv(self.taxonomy_file, header=[0])
        accession_ind = tax_db.index[tax_db["accession_number"] == valid_accession].to_list()[0]
        requested_tax = tax_db.iloc[accession_ind]
        return requested_tax

    def export_record(self, valid_accession):
        '''Method is used to export single sequence in a form of SeqIO record and corresponding taxonomy record in a form of numpy.Series'''
        tax_db = pd.read_csv(self.taxonomy_file, header=[0])
        seq_db = SeqIO.to_dict(SeqIO.parse(self.sequence_file, "fasta"))
        accession_ind = tax_db.index[tax_db["accession_number"] == valid_accession].to_list()[0]
        requested_tax = tax_db.iloc[accession_ind]
        requested_seq = seq_db[valid_accession]
        return requested_tax, requested_seq


class Query_ncbi:
    #Finished (unit)
    def __init__(self, database, email, alphabet):
        self.database = database
        self.email = email
        self.alphabet = alphabet

    def check_output(self, valid_accession):
        '''Method checks if record exists in NCBI database given accession number.'''
        Entrez.email = self.email
        try:
            handle = Entrez.efetch(db=self.database, id = valid_accession, rettype="acc") #Attempts to open connection to NCBI database
            data = handle.read() #Reads up-to-date accession from NCBI
            handle.close() #Closes connection
            if valid_accession in data: #Checks if found accession contains query
                return True
            else: 
                return False
        except urllib.error.HTTPError as e: #If query is invalid, the exception is thrown
            if str(e) == "HTTP Error 400: Bad Request":
                return False

    def get_fasta(self, valid_accession):
        '''Method attempts to get fasta sequence (header + sequence separately) given accession number.'''
        #generate request
        Entrez.email = self.email
        handle = Entrez.efetch(db=self.database, id = valid_accession, rettype="fasta") #Attempts to open connection to NCBI database
        record = SeqIO.read(handle, "fasta") #Reads sequence in fasta format from ncbi
        handle.close() #Closes connection
        return record.seq, record.id

    def get_taxonomy(self, valid_accession):
        '''Method attempts to get taxonomy information(list) from NCBI database given accession number.'''
        Entrez.email = self.email
        handle = Entrez.efetch(db=self.database, id = valid_accession, rettype="gb") #Attempts to open connection to NCBI database
        tax_data = SeqIO.read(handle, format='genbank').annotations['taxonomy']
        handle.close() #Closes connection
        return tax_data


class Logger:
    #Finished (unit)
    def __init__(self, operation_type, valid_accession=None,  taxonomy=None,  old_accession=None,  old_taxonomy=None,  new_accession=None,  new_taxonomy=None, log_file='PD2.log'):
        self.operation_type = operation_type
        self.log_file = log_file
        self.log_dict = {
        "add_fasta":f"New record was added from fasta file (id: {valid_accession})",
        "add_ncbi":f"New record was added from ncbi database (id: {valid_accession})",
        "rm_record":f"Record was removed (id: {valid_accession})",
        "ch_header":f"ID of the record was changed from {old_accession} to {new_accession}",
        "ch_tax":f"Taxonomy information for {valid_accession} was changed from {old_taxonomy} to {new_taxonomy}"
    }

    def log_change(self):
        '''Method is used to log local changes to database files'''
        #Create log file if it does not exist
        log_file = Path(self.log_file)
        log_file.touch(exist_ok=True)
        
        #Log changes - full documentation link - https://docs.python.org/3/howto/logging.html
        pd2_logger = logging.getLogger(self.operation_type)
        pd2_logger.setLevel(logging.DEBUG)
        log_file_handler = logging.FileHandler(filename=self.log_file)
        log_file_formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S')
        log_file_handler.setFormatter(log_file_formatter)
        pd2_logger.addHandler(log_file_handler)
        pd2_logger.info(self.log_dict[self.operation_type])
        log_file_handler.close() #Close file after logging is complete


class Plotter:
    #Finished (unit)
    def __init__(self, adj_set, count_dict):
        self.adj_set = adj_set
        self.count_dict = count_dict

    def display(self):
        '''Method is used to display current content of the local database'''
        nr_vertices = len(self.count_dict.keys())
        v_label = [f'{key}: {self.count_dict[key]}' for key in self.count_dict.keys()]
        graph = Graph()
        graph.add_vertices(nr_vertices)
        graph.add_edges(list(self.adj_set))
        lay = graph.layout('rt')
        max_y = max([lay[k][1] for k in range(nr_vertices)])

        es = EdgeSeq(graph) # sequence of edges
        E = [e.tuple for e in graph.es] # list of edges

        Xn = [lay[k][0] for k in range(nr_vertices)]
        Yn = [2*max_y-lay[k][1] for k in range(nr_vertices)]
        Xe = []
        Ye = []
        for edge in E:
            Xe+=[lay[edge[0]][0],lay[edge[1]][0], None]
            Ye+=[2*max_y-lay[edge[0]][1],2*max_y-lay[edge[1]][1], None]

        labels = v_label
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=Xe, y=Ye, mode='lines', line=dict(color='rgb(210,210,210)', width=1), hoverinfo='none'))
        fig.add_trace(go.Scatter(x=Xn, y=Yn, mode='markers', name='bla', marker=dict(symbol='circle-dot', size=100, color='#6175c1',    #'#DB4551',
                                        line=dict(color='rgb(50,50,50)', width=1)), text=labels, hoverinfo='text', opacity=0.8))


        def make_annotations(pos, text, font_size=15, font_color='rgb(0,0,0)'):
            L=len(pos)
            if len(text)!=L:
                raise ValueError('The lists pos and text must have the same len')
            annotations = []
            for k in range(L):
                annotations.append(
                    # or replace labels with a different list for the text within the circle
                    dict(text=labels[k], x=pos[k][0], y=2*max_y-lay[k][1], xref='x1', yref='y1', font=dict(color=font_color, size=font_size), showarrow=False)
                )
            return annotations

        axis = dict(showline=False, zeroline=False, showgrid=False, showticklabels=False,) # hide axis line, grid, ticklabels and  title

        fig.update_layout(title= 'Local database summary', annotations=make_annotations(lay, v_label), font_size=14, showlegend=False,
                      xaxis=axis, yaxis=axis, margin=dict(l=40, r=40, b=85, t=100), hovermode='closest', plot_bgcolor='rgb(143, 150, 196)')
        fig.show()


if __name__ == "__main__":
    my_interface = Interface('ACGT', 'csv', r"^[A-z]{2}_[A-Z0-9]*$")
    arg_dict = vars(my_interface.parse_arguments())

    if any([True if arg else False for arg in arg_dict.values()]):
        my_database = Database('my_database')
        my_database.create_db_files()
        my_qry = Query_ncbi('nucleotide', 'jb17048@edu.lu.lv', 'ACGT')

    if arg_dict['add_fasta']:
        file_check = my_interface.check_file_type(f'{arg_dict["add_fasta"]}')
        if file_check:
            records = my_interface.read_local(arg_dict['add_fasta'])
            sequences, taxonomy = records[0], records[1]
            for key in sequences.keys():
                acc_nr = sequences[key].id
                sqnc = sequences[key].seq
                tax_ind = taxonomy.index[taxonomy['accession_number'] == key].to_list()[0]
                tax_str = taxonomy.iloc[tax_ind]['taxonomy_string']
                ab_check = my_interface.check_alphabet(sqnc)
                id_check = my_interface.check_format(acc_nr)
                dupl_check = my_database.find_id(acc_nr)
                descr = f'from local file - {arg_dict["add_fasta"]}'
                if all([ab_check,id_check]) and not dupl_check:
                    my_database.add_record(acc_nr,sqnc,tax_str,descr)
                    my_database.calculate_content(taxonomy_string=tax_str)
                    my_logger = Logger("add_fasta",acc_nr)
                    my_logger.log_change()
                else:
                    if (not ab_check) and (not id_check):
                        sys.exit(f'Expected alphabet & Expected id pattern(regex): {my_interface.accession_pattern}|{my_interface.alphabet}')
                    elif not ab_check:
                        sys.exit(f'Expected alphabet: {my_interface.alphabet}')
                    elif not id_check:
                        sys.exit(f'Expected id pattern(regex): {my_interface.accession_pattern}')
                    elif dupl_check:
                        sys.exit(f'Local database already contain a sequence with given accession number.')
                    
        else:
            sys.exit(f'Files with expected type do not exist. Expected:\n {arg_dict["add_fasta"]}.{my_interface.valid_input_type}\n{arg_dict["add_fasta"]}.fasta')

    if arg_dict['add_ncbi']:
        id_check = my_interface.check_format(arg_dict['add_ncbi'])
        dupl_check = my_database.find_id(arg_dict['add_ncbi'])
        if id_check:
            if not dupl_check:
                request_check = my_qry.check_output(arg_dict['add_ncbi'])
                if request_check:
                    output_seq = my_qry.get_fasta(arg_dict['add_ncbi'])
                    sqnc = output_seq[0]
                    acc_nr = arg_dict['add_ncbi']
                    tax_str = "|".join(my_qry.get_taxonomy(arg_dict['add_ncbi']))
                    descr = 'added from ncbi'
                    my_database.add_record(acc_nr,sqnc,tax_str,descr)
                    my_database.calculate_content(taxonomy_string=tax_str)
                    my_logger = Logger("add_ncbi",valid_accession=arg_dict['add_ncbi'])
                    my_logger.log_change()
            else:
                sys.exit(f'Local database already contain a sequence with given accession number.')
        else:
            sys.exit(f'Accession id format is not valid. Expected(regex): {my_interface.accession_pattern}')
        
    if arg_dict['add_ncbi_list']:
        file_check = os.path.exists(f'{arg_dict["add_ncbi_list"]}')
        if file_check:
            record_list = list(pd.read_csv(arg_dict['add_ncbi_list'],header=[0]).iloc[:, 0])
            for acc_nr in record_list:
                id_check = my_interface.check_format(acc_nr)
                dupl_check = my_database.find_id(acc_nr)
                if id_check:
                    if not dupl_check:
                        request_check = my_qry.check_output(acc_nr)
                        if request_check:
                            output_seq = my_qry.get_fasta(acc_nr)
                            sqnc = output_seq[0]
                            tax_str = "|".join(my_qry.get_taxonomy(acc_nr))
                            descr = 'added from ncbi'
                            my_database.add_record(acc_nr,sqnc,tax_str,descr)
                            my_database.calculate_content(taxonomy_string=tax_str)
                            my_logger = Logger("add_ncbi",valid_accession=acc_nr)
                            my_logger.log_change()
                    else:
                        print(f'Local database already contain a sequence with given accession number: {acc_nr}')
                else:
                    print(f'Accession id format is not valid: {acc_nr} Expected(regex): {my_interface.accession_pattern}')
        else:
            sys.exit(f'File with expected type do not exist. Expected:\n {arg_dict["add_ncbi_list"]}.{my_interface.valid_input_type}')

    if arg_dict['exp_fasta']:
        file_check = os.path.exists(f'{arg_dict["exp_fasta"]}')
        if file_check:
            record_list = list(pd.read_csv(arg_dict['exp_fasta'],header=[0]).iloc[:, 0])
            out_dict = {}
            for acc_nr in record_list:
                exists = my_database.find_id(acc_nr)
                if exists:
                    out_dict[acc_nr] = my_database.export_fasta(acc_nr)
                else:
                    print(f'Sequence with given accession number is not stored in local database: {acc_nr}')
            with open(f'exported_sequences.fasta', 'w') as handle:
                SeqIO.write(out_dict.values(), handle, 'fasta')
            sys.exit("Exported available sequences to exported_sequences.fasta file")
        else:
            sys.exit(f'File with expected type do not exist. Expected:\n {arg_dict["exp_fasta"]}.{my_interface.valid_input_type}')

    if arg_dict['exp_meta']:
        file_check = os.path.exists(f'{arg_dict["exp_meta"]}')
        if file_check:
            record_list = list(pd.read_csv(arg_dict['exp_meta'],header=[0]).iloc[:, 0])
            out_df = pd.DataFrame(columns=["accession_number", "taxonomy_string"])
            for acc_nr in record_list:
                exists = my_database.find_id(acc_nr)
                if exists:
                    record = my_database.export_tax(acc_nr)
                    out_df = out_df.append(record)
                else:
                    print(f'Sequence with given accession number is not stored in local database: {acc_nr}')
            out_df.to_csv(f'exported_taxonomy.csv',header=True, index=False)
            sys.exit("Exported available taxonomies to exported_taxonomy.csv file")
        else:
            sys.exit(f'File with expected type do not exist. Expected:\n {arg_dict["exp_meta"]}.{my_interface.valid_input_type}')

    if arg_dict['exp_records']:
        file_check = os.path.exists(f'{arg_dict["exp_records"]}')
        if file_check:
            record_list = list(pd.read_csv(arg_dict['exp_records'],header=[0]).iloc[:, 0])
            out_df = pd.DataFrame(columns=["accession_number", "taxonomy_string"])
            out_dict = {}
            for acc_nr in record_list:
                exists = my_database.find_id(acc_nr)
                if exists:
                    record = my_database.export_tax(acc_nr)
                    out_df = out_df.append(record)
                    out_dict[acc_nr] = my_database.export_fasta(acc_nr)
                else:
                    print(f'Sequence with given accession number is not stored in local database: {acc_nr}')
            out_df.to_csv(f'exported_taxonomy.csv',header=True, index=False)
            with open(f'exported_sequences.fasta', 'w') as handle:
                SeqIO.write(out_dict.values(), handle, 'fasta')
            sys.exit("Exported available taxonomies to exported_taxonomy.csv file\nExported available sequences to exported_sequences.fasta file")
        else:
            sys.exit(f'File with expected type do not exist. Expected:\n {arg_dict["exp_records"]}.{my_interface.valid_input_type}')

    if arg_dict['rm_record']:
        exists = my_database.find_id(arg_dict['rm_record'])
        if exists:
            my_database.rm_record(arg_dict['rm_record'])
            my_logger = Logger("rm_record", valid_accession=arg_dict['rm_record'])
            my_logger.log_change()
        else:
            sys.exit('Sequence with given accession number is not stored in local database.')

    if arg_dict['ch_header']:
        old_id = arg_dict['ch_header'].split(",")[0]
        new_id = arg_dict['ch_header'].split(",")[1]
        id_check_old = my_interface.check_format(old_id)
        id_check_new = my_interface.check_format(new_id)
        id_exists_new = my_database.find_id(new_id)
        exists = my_database.find_id(old_id)
        if id_check_old:
            if exists:
                if id_check_new:
                    if not id_exists_new:
                        my_database.write_id(old_id, new_id)
                        my_logger = Logger("ch_header", old_accession=old_id, new_accession=new_id)
                        my_logger.log_change()
                    else:
                        sys.exit(f'New id already exists in the database: {new_id}')
                else:
                    sys.exit(f'New id format is not valid: {new_id} Expected(regex): {my_interface.accession_pattern}')
            else:
                sys.exit(f'Sequence with given accession number is not stored in local database: {old_id}')
        else:
            sys.exit(f'Old id format is not valid: {old_id} Expected(regex): {my_interface.accession_pattern}')

    if arg_dict['ch_tax']:
        id = arg_dict['ch_tax'].split(",")[0]
        new_tax = arg_dict['ch_tax'].split(",")[1]
        id_check = my_interface.check_format(id)
        exists = my_database.find_id(id)
        old_tax = my_database.find_tax(id)
        
        if id_check:
            if exists:
                my_database.write_tax(id,new_tax)
                my_logger = Logger("ch_tax", valid_accession=id, old_taxonomy=old_tax, new_taxonomy=new_tax)
                my_logger.log_change()
            else:
                sys.exit(f'Sequence with given accession number is not stored in local database: {old_id}')
        else:
            sys.exit(f'Accession format is not valid: {old_id} Expected(regex): {my_interface.accession_pattern}')



    if arg_dict['view_data']:
        count_data = my_database.calculate_content()
        my_plotter = Plotter(count_data[0],count_data[1])
        my_plotter.display()