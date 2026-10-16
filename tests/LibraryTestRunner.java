package moe.practice;
import android.app.*;import android.os.*;
public final class LibraryTestRunner extends Instrumentation {
 @Override public void onCreate(Bundle options){super.onCreate(options);start();}
 @Override public void onStart(){Bundle result=new Bundle();try{
  java.io.File root=new java.io.File(getTargetContext().getFilesDir(),"cover-regression-r3");
  PackCoverRegression.main(new String[]{root.getAbsolutePath()});
  LibraryRegression.main(new String[]{"/data/local/tmp/full-packlist.json","/data/local/tmp/shell-packlist.json"});
  result.putString("stream","PackCoverRegression PASS checks="+PackCoverRegression.checks+"; LibraryRegression PASS checks="+LibraryRegression.checks+"\n");finish(Activity.RESULT_OK,result);
 }catch(Throwable failure){result.putString("stream",android.util.Log.getStackTraceString(failure));finish(Activity.RESULT_CANCELED,result);}}
}
