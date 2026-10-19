# [복원] ILO(Gmyrek 외 2025) 업무별 점수 → ISCO-08 직업별 2025 평균(mean_score_2025, 소수 둘째 자리). 원본 isco_occ.csv와 바이트 단위로 같음을 확인함.
import pandas as pd
x=pd.read_excel('dl2/Final_Scores_ISCO08_Gmyrek_et_al_2025.xlsx')
g=x.groupby('ISCO_08').agg(t=('Title','first'),m=('mean_score_2025','first')).reset_index()
g['m']=g.m.round(2);g.to_csv('isco_occ.csv',index=False);print('isco',len(g))
