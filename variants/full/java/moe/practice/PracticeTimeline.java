package moe.practice;

import android.content.Context;
import android.graphics.*;
import android.media.*;
import android.view.*;
import java.io.*;
import java.nio.*;
import java.util.Locale;

/** A waveform transport over the game's own 3D scene, never a chart renderer. */
final class PracticeTimeline extends View {
    interface Listener { void seek(int time); void marker(boolean start,int time); }
    private final Paint paint=new Paint(3);
    private final Listener listener;
    private int duration=1000,cursor,a,b=1000,drag=-1,offset;
    private float[] waveform;
    private String path="",message="正在读取音乐波形…";
    private volatile int generation;
    PracticeTimeline(Context context,Listener callback){super(context);listener=callback;setContentDescription("谱面时间轴，拖动定位，A 和 B 为片段边界");}
    void state(int length,int time,int start,int end){duration=Math.max(1000,length);if(drag<0)cursor=time;a=start;b=end;invalidate();}
    int position(){return cursor;}
    boolean dragging(){return drag>=0;}
    private float x(int time){return 18+(getWidth()-36)*Math.max(0,Math.min(1,time/(float)duration));}
    private int time(float x){return Math.max(0,Math.min(duration-1,Math.round((x-18)/Math.max(1,getWidth()-36)*duration)));}
    @Override protected void onDraw(Canvas c){
        super.onDraw(c);int w=getWidth(),h=getHeight();c.drawColor(0x9a15101f);
        paint.setColor(0x4043d4ee);c.drawRect(x(a),12,x(b),h-25,paint);
        if(waveform!=null){for(int i=0;i<waveform.length;i++){float xx=18+(w-36)*i/(float)(waveform.length-1);paint.setColor(xx<=x(cursor)?0xff73d5ec:0xff766c82);float amp=waveform[i]*(h-42)*.46f;c.drawLine(xx,(h-25)*.5f-amp,xx,(h-25)*.5f+amp,paint);}}
        else {paint.setColor(0xffbcb2c8);paint.setTextSize(h*.15f);c.drawText(message,24,h*.5f,paint);}
        paint.setStrokeWidth(2);paint.setColor(0xfff6d37c);c.drawLine(x(a),8,x(a),h-22,paint);paint.setColor(0xffda8dfa);c.drawLine(x(b),8,x(b),h-22,paint);
        paint.setColor(Color.WHITE);c.drawLine(x(cursor),6,x(cursor),h-22,paint);c.drawCircle(x(cursor),(h-25)*.5f,5,paint);
        paint.setTextSize(h*.16f);c.drawText("A",x(a)+3,20,paint);c.drawText("B",x(b)-15,20,paint);
        c.drawText(String.format(Locale.US,"%.3fs / %.3fs   ·   拖动整张谱面，拖动 A / B 选择片段",cursor/1000f,duration/1000f),20,h-7,paint);
    }
    @Override public boolean onTouchEvent(MotionEvent event){
        switch(event.getActionMasked()){
        case MotionEvent.ACTION_DOWN:
            getParent().requestDisallowInterceptTouchEvent(true);
            float xx=event.getX(),threshold=24*getResources().getDisplayMetrics().density;
            // Handles occupy the upper band, so the waveform remains seekable everywhere.
            drag=event.getY()<getHeight()*.28f&&Math.abs(xx-x(a))<threshold?1:event.getY()<getHeight()*.28f&&Math.abs(xx-x(b))<threshold?2:0;
        case MotionEvent.ACTION_MOVE:
            cursor=time(event.getX());
            if(drag==1){a=Math.min(cursor,b-1000);cursor=Math.max(0,a);listener.marker(true,cursor);}
            if(drag==2){b=Math.max(cursor,a+1000);cursor=Math.min(duration-1,b);listener.marker(false,cursor);}
            listener.seek(cursor);invalidate();return true;
        case MotionEvent.ACTION_UP:performClick();drag=-1;return true;
        case MotionEvent.ACTION_CANCEL:drag=-1;return true;
        }return true;
    }
    @Override public boolean performClick(){super.performClick();return true;}
    private InputStream asset(String name)throws IOException{File local=new File(ChartLibrary.root(getContext()),name);return local.isFile()?new FileInputStream(local):getContext().getAssets().open(name);}
    void load(String name){
        if(name==null||name.isEmpty()||name.equals(path))return;path=name;int token=++generation;waveform=null;message="正在读取音乐波形…";
        new Thread(()->{
            MediaExtractor extractor=null;MediaCodec codec=null;File cached=null;
            try{
                String aff;try(InputStream in=asset(name)){aff=new String(ChartLibrary.read(in),"UTF-8");}
                java.util.regex.Matcher m=java.util.regex.Pattern.compile("AudioOffset\\s*:\\s*(-?\\d+)").matcher(aff);final int audioOffset=m.find()?Integer.parseInt(m.group(1)):0;
                String directory=name.substring(0,name.lastIndexOf('/')+1),stem=name.substring(name.lastIndexOf('/')+1).replace(".aff","");
                cached=File.createTempFile("wave-",".ogg",getContext().getCacheDir());
                InputStream audio;try{audio=asset(directory+stem+".ogg");}catch(IOException e){audio=asset(directory+"base.ogg");}
                try(InputStream in=audio;OutputStream out=new FileOutputStream(cached)){byte[] buf=new byte[65536];int n;while((n=in.read(buf))>=0){if(token!=generation)return;out.write(buf,0,n);}}
                extractor=new MediaExtractor();extractor.setDataSource(cached.getAbsolutePath());MediaFormat format=null;
                for(int i=0;i<extractor.getTrackCount();i++){MediaFormat candidate=extractor.getTrackFormat(i);if(candidate.getString(MediaFormat.KEY_MIME).startsWith("audio/")){format=candidate;extractor.selectTrack(i);break;}}
                if(format==null)throw new IOException("没有音轨");
                long audioDuration=format.containsKey(MediaFormat.KEY_DURATION)?format.getLong(MediaFormat.KEY_DURATION):duration*1000L;
                final int length=Math.max(duration,(int)Math.min(3600000,audioDuration/1000+Math.max(0,audioOffset)));
                final float[] peaks=new float[1536];codec=MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME));codec.configure(format,null,null,0);codec.start();
                boolean inputEnded=false,outputEnded=false;int channels=format.getInteger(MediaFormat.KEY_CHANNEL_COUNT),rate=format.getInteger(MediaFormat.KEY_SAMPLE_RATE),encoding=AudioFormat.ENCODING_PCM_16BIT;
                MediaCodec.BufferInfo info=new MediaCodec.BufferInfo();long deadline=android.os.SystemClock.elapsedRealtime()+120000;
                while(!outputEnded&&token==generation){
                    if(android.os.SystemClock.elapsedRealtime()>deadline)throw new IOException("波形读取超时");
                    if(!inputEnded){int index=codec.dequeueInputBuffer(1000);if(index>=0){ByteBuffer input=codec.getInputBuffer(index);int count=extractor.readSampleData(input,0);if(count<0){codec.queueInputBuffer(index,0,0,0,MediaCodec.BUFFER_FLAG_END_OF_STREAM);inputEnded=true;}else{codec.queueInputBuffer(index,0,count,extractor.getSampleTime(),0);extractor.advance();}}}
                    int index=codec.dequeueOutputBuffer(info,1000);
                    if(index==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED){MediaFormat output=codec.getOutputFormat();channels=output.getInteger(MediaFormat.KEY_CHANNEL_COUNT);rate=output.getInteger(MediaFormat.KEY_SAMPLE_RATE);if(output.containsKey(MediaFormat.KEY_PCM_ENCODING))encoding=output.getInteger(MediaFormat.KEY_PCM_ENCODING);}
                    else if(index>=0){ByteBuffer pcm=codec.getOutputBuffer(index).duplicate().order(ByteOrder.LITTLE_ENDIAN);pcm.position(info.offset);pcm.limit(info.offset+info.size);int bytes=encoding==AudioFormat.ENCODING_PCM_FLOAT?4:2,frame=0;
                        while(pcm.remaining()>=bytes*channels){float peak=0;for(int ch=0;ch<channels;ch++){float sample=bytes==4?pcm.getFloat():pcm.getShort()/32768f;peak=Math.max(peak,Math.abs(sample));}long chartUs=info.presentationTimeUs+audioOffset*1000L+frame++*1000000L/rate;int bin=(int)(chartUs*peaks.length/(length*1000L));if(bin>=0&&bin<peaks.length)peaks[bin]=Math.max(peaks[bin],peak);}
                        outputEnded=(info.flags&MediaCodec.BUFFER_FLAG_END_OF_STREAM)!=0;codec.releaseOutputBuffer(index,false);
                    }
                }
                if(token!=generation)return;
                post(()->{if(token!=generation)return;offset=audioOffset;waveform=peaks;duration=length;invalidate();});
            }catch(Exception e){post(()->{if(token==generation){message="音乐波形暂不可用 · 时间轴仍可拖动";invalidate();}});}
            finally{if(codec!=null){try{codec.stop();}catch(Exception ignored){}codec.release();}if(extractor!=null)extractor.release();if(cached!=null)cached.delete();}
        },"practice-waveform").start();
    }
}
