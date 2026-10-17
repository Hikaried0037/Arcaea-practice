"""Run the final Arc701 plugin against the matching 7.0.1c game clock."""
import argparse,json
from pathlib import Path
from compiled_settings_test import exercise as settings
from compiled_clock_test import exercise as clock
from compiled_sync_test import exercise as smooth

def main():
 p=argparse.ArgumentParser();p.add_argument('--plugin',required=True);p.add_argument('--game',required=True);p.add_argument('--report',type=Path);a=p.parse_args();profile=(0x10107a0,0x110eb0c,0x928828,0x1b59e30)
 result={'result':'passed','profile':'Arc701 7.0.1c ARM64','settings_cases':settings(a.plugin,a.game,profile),'clock_cases':clock(a.plugin,a.game,profile),'smooth_cases':smooth(a.plugin,a.game,profile),'limitations':'Synthetic ARM64 execution; no physical headphone or GPU measurement'}
 text=json.dumps(result,indent=2)+'\n';print(text)
 if a.report:a.report.write_text(text,encoding='utf-8')
if __name__=='__main__':main()
