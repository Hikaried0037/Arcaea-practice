package moe.practice;
import java.io.*;
import java.nio.*;
import java.nio.charset.*;
import java.util.regex.*;
final class ChartFormat {
    private static final Pattern OFFSET=Pattern.compile("AudioOffset\\s*:\\s*([+-]?\\d+)",Pattern.CASE_INSENSITIVE);
    private static final Pattern TIMING=Pattern.compile("(?<![A-Za-z])timing\\s*\\(");
    private static final Pattern EVENT=Pattern.compile("(?<![A-Za-z])(?:hold|arc|timing|camera|scenecontrol)?\\s*\\(\\s*[+-]?\\d+\\s*,");
    static String decode(byte[] bytes)throws IOException {
        Charset charset=StandardCharsets.UTF_8;
        if(bytes.length>=2&&((bytes[0]==(byte)0xff&&bytes[1]==(byte)0xfe)||(bytes[0]==(byte)0xfe&&bytes[1]==(byte)0xff)))charset=StandardCharsets.UTF_16;
        try{return normalize(charset.newDecoder().onMalformedInput(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString());}
        catch(CharacterCodingException e){throw new IOException("AFF 文字编码无效，请使用 UTF-8 或带 BOM 的 UTF-16",e);}
    }
    static String normalize(String aff){return aff.replace("\uFEFF","").replace("\r\n","\n").replace('\r','\n');}
    static void validate(String input)throws IOException {
        if(input.length()>16*1024*1024)throw new IOException("AFF 大于 16 MiB");
        String aff=normalize(input);boolean offset=false,separator=false,timing=false,event=false;int depth=0,lineNumber=0;
        try(BufferedReader reader=new BufferedReader(new StringReader(aff))){String line;
            while((line=reader.readLine())!=null){lineNumber++;int comment=line.indexOf("//");if(comment>=0)line=line.substring(0,comment);line=line.trim();if(line.isEmpty())continue;
                if(!separator){if(line.equals("-")){separator=true;continue;}Matcher m=OFFSET.matcher(line);if(m.matches()){try{Integer.parseInt(m.group(1));offset=true;}catch(NumberFormatException e){throw new IOException("AudioOffset 超出整数范围");}}continue;}
                timing|=TIMING.matcher(line).find();event|=EVENT.matcher(line).find();
                for(int i=0;i<line.length();i++){char ch=line.charAt(i);if(ch=='(')depth++;else if(ch==')'&&--depth<0)throw new IOException("AFF 第 "+lineNumber+" 行括号不匹配");}
            }
        }
        if(!offset)throw new IOException("AFF 缺少有效 AudioOffset 头部");
        if(!separator)throw new IOException("AFF 缺少独立的 - 分隔行");
        if(!timing)throw new IOException("AFF 缺少 timing 事件");
        if(depth!=0)throw new IOException("AFF 括号不匹配");
        if(!event)throw new IOException("AFF 没有可识别事件");
    }
}
