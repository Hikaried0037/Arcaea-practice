package moe.practice;

import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.*;
import java.io.File;

/** Permission and resource checks must finish before the native engine starts. */
public final class ExternalBootstrap extends Activity {
    @Override public void onCreate(Bundle state){super.onCreate(state);check();}
    private void check(){
        if(Build.VERSION.SDK_INT>=23&&checkSelfPermission("android.permission.WRITE_EXTERNAL_STORAGE")!=PackageManager.PERMISSION_GRANTED){
            requestPermissions(new String[]{"android.permission.READ_EXTERNAL_STORAGE","android.permission.WRITE_EXTERNAL_STORAGE"},61310);return;
        }
        File root=ChartLibrary.root(this);
        if(!new File(root,"songs/songlist").isFile()||!new File(root,"songs/packlist").isFile()||!new File(root,"img").isDirectory()){
            new AlertDialog.Builder(this).setTitle("请先解压游戏资源").setMessage("将 Arc61310.zip 解压到内部存储，确保存在：\n/storage/emulated/0/Arc61310/songs/songlist\n\n避免多套一层 Arc61310 文件夹。完成后点击重试。").setPositiveButton("重试",(d,n)->check()).setNegativeButton("退出",(d,n)->finish()).show();return;
        }
        if(!root.canWrite()){
            new AlertDialog.Builder(this).setMessage("无法写入 Arc61310 文件夹，请在系统设置中允许文件访问。").setPositiveButton("重试",(d,n)->check()).setNegativeButton("退出",(d,n)->finish()).show();return;
        }
        Intent i=new Intent();i.setClassName(this,"low.moe.AppActivity");startActivity(i);finish();
    }
    @Override public void onRequestPermissionsResult(int code,String[] names,int[] grants){
        super.onRequestPermissionsResult(code,names,grants);
        if(code==61310){if(grants.length>0&&grants[0]==PackageManager.PERMISSION_GRANTED)check();else new AlertDialog.Builder(this).setMessage("游戏通过 Arc61310 文件夹运行，需要文件访问权限。").setPositiveButton("重试",(d,n)->check()).setNegativeButton("退出",(d,n)->finish()).show();}
    }
}
