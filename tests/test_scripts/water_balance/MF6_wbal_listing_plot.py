#%% imports
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

#%% functions
def end_balance(line):
    if("\n" in line and len(line)==1):
        return True
    return False

def append_items_dict_list(dict,label,value):
    if label in dict:
        dict[label].append(value)
    else:
        dict[label] = [value]
    return dict
      
#%% path variables
output_dir = Path(r"c:\werkmap")
model_name = 'T-MODEL-D'
path_mf_listing = r"c:\werkmap\Lumbricus_MF6\test-modellen\mf6\T-MODEL-D\GWF_1"
    
#%% read listing to dict and pd-dataframe
file_in = open(path_mf_listing + '/' + model_name + '.LST', 'r')

data_out = {}
data_out_cummulative = {}
time = 0
while True:
    line=file_in.readline()
    if not line:
        break
    if("IN:" in line):
        time+=1
        append_items_dict_list(data_out,'PERIOD',time)
        line=file_in.readline()  #dummy line containing '---'
        while True:
            line=file_in.readline()
            if(end_balance(line)):
                break
            line_list=line.split()
            data_out = append_items_dict_list(data_out,line_list[6]+'_IN',line_list[5])
            data_out_cummulative = append_items_dict_list(data_out_cummulative,line_list[6]+'_IN',line_list[2])
    elif("TOTAL IN" in line):
        line_list=line.split()
        data_out = append_items_dict_list(data_out,'TOTAL_IN',line_list[7])
        data_out_cummulative = append_items_dict_list(data_out_cummulative,'TOTAL_IN',line_list[3])
    elif("OUT:" in line):
        line=file_in.readline()
        while True:
            line=file_in.readline()
            if(end_balance(line)):
                break
            line_list=line.split()
            # make outgoing flux negative
            data_out = append_items_dict_list(data_out,line_list[6]+'_OUT','-'+line_list[5])
            data_out_cummulative = append_items_dict_list(data_out_cummulative,line_list[6]+'_OUT','-'+line_list[2])
    elif("TOTAL OUT" in line):
        line_list=line.split()
        data_out = append_items_dict_list(data_out,'TOTAL_OUT',line_list[7])
        data_out_cummulative = append_items_dict_list(data_out_cummulative,'TOTAL_OUT',line_list[3])
    elif("IN - OUT" in line):
        line_list=line.split()
        data_out = append_items_dict_list(data_out,'TOTAL_IN-OUT',line_list[9])
        data_out_cummulative = append_items_dict_list(data_out_cummulative,'TOTAL_IN-OUT',line_list[4])

file_in.close()

df_data_out = pd.DataFrame(data_out)
df_data_out_cummulative = pd.DataFrame(data_out_cummulative)
df_data_out.to_csv(output_dir / 'waterbalance.csv',index=False)
df_data_out_cummulative.to_csv('waterbalance_cummulative.csv',index=False)

#%%

plot_name = model_name

wbal = pd.read_csv(output_dir / 'waterbalance.csv', sep=',')
ymin = min(wbal.min(numeric_only=True))
ymax = max(wbal.max(numeric_only=True))
nrow ,nitem = wbal.shape
nwbal = int((nitem-4)/2)

#%%
cmap = mpl.cm.get_cmap('Spectral')
fig = plt.figure()
ax = plt.subplot(111)
plt.title('water balance: '+ plot_name)
plt.xlabel('days')
plt.ylabel('flux [m3/d]')
plt.ylim([ymin, ymax])

bot=[0]*nrow
labels=[]
col=[]
item=int((nitem-4)/2)
i_item=0
for (i, colname) in enumerate(wbal):
    if('TOTAL_IN-OUT' in colname):
        break
    if('TOTAL_IN' not in colname and 'TOTAL_OUT' not in colname and i>0):
        i_item+=1
        if(i_item <= item):
            rgba = cmap(i_item/(item))
            ilen=len(colname)-3
            labels.append(colname[0:ilen])
        else:
            rgba = cmap((i_item-item)/(item))
        plt.bar(wbal['PERIOD'], wbal.iloc[:,i],bottom=bot,color=rgba)
        plt.title('water balance: '+ plot_name)
        plt.xlabel('days')
        plt.ylabel('flux [m3/d]')
        plt.ylim([ymin, ymax])
        if(max(wbal.iloc[:,i]) < 0):
            bot=wbal.iloc[:,i]
        else:
            bot=wbal.iloc[:,i]
box = ax.get_position()
ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
ax.legend(labels,loc='center left', bbox_to_anchor=(1, 0.5))
plt.show()

    






#%%




