/*
USER_ID: bupt#sdmda_admin2_3
PROBLEM: 74
SUBMISSION_TIME: 2014-01-07 16:07:18
*/
#include<iostream>
using namespace std;
int main()
{
     int a=-1001,b=1001;
     cin>>a>>b;
     if(a>=-1000&&a<=1000&&b>=-1000&&b<=1000&&a!=b)
     {
        if(a>=b)cout<<a-b<<endl;
        else cout<<b-a<<endl;
     }
     else cout<<"error."<<endl;
     //system("pause");
     return 0;
}//共计14行代码 