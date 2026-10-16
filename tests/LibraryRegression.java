package moe.practice;
import org.json.*;
import java.util.*;
import java.nio.file.*;
public final class LibraryRegression {
    static int checks;
    static void check(boolean value,String name){checks++;if(!value)throw new AssertionError(name);}
    static LibraryCatalog fixture()throws Exception {
        JSONArray packs=new JSONArray().put(LibraryCatalog.newPack("base","Arcaea","arcaea"))
            .put(LibraryCatalog.newPack("p","原曲包","mainstory")).put(LibraryCatalog.newPack("child","子曲包","mainstory").put("pack_parent","p"));
        JSONArray songs=new JSONArray();for(int i=0;i<3;i++)songs.put(new JSONObject().put("id","s"+i).put("idx",i).put("set",i==0?"base":i==1?"p":"child").put("artist","曲师").put("unknown",new JSONObject().put("keep",true)));
        return new LibraryCatalog(new JSONObject().put("songs",songs),new JSONObject().put("packs",packs));
    }
    public static void main(String[] args)throws Exception {
        LibraryCatalog m=fixture();String pretty=LibraryCatalog.pretty(m.songs);
        check(pretty.startsWith("{\n    \"songs\": [\n"),"four-space root indentation");
        check(pretty.contains("\n        {\n            \""),"nested object indentation");
        check(pretty.contains("曲师"),"unicode remains readable");
        check(new JSONObject(pretty).getJSONArray("songs").getJSONObject(0).getInt("idx")==0,"numeric types unchanged");
        JSONObject ordered=new JSONObject().put("difficulties",new JSONArray().put(new JSONObject().put("rating",12).put("chartDesigner","谱师").put("ratingClass",3))).put("id","test").put("idx",9).put("title_localized",new JSONObject().put("en","Quote \" / 换行\n"));
        String canonical=LibraryCatalog.pretty(ordered);check(canonical.indexOf("\"idx\"")<canonical.indexOf("\"id\""),"song idx precedes id");
        check(canonical.indexOf("\"ratingClass\"")<canonical.indexOf("\"chartDesigner\"")&&canonical.indexOf("\"chartDesigner\"")<canonical.indexOf("\"rating\""),"difficulty field order");
        check(new JSONObject(canonical).getJSONObject("title_localized").getString("en").equals("Quote \" / 换行\n"),"quoted and multiline names round trip");
        check(!LibraryCatalog.newPack("new","新曲包","arcaea").getBoolean("is_extend_pack"),"new packs do not require world extend unlocks");
        m.deleteSong("s1");check(m.songs.getJSONArray("songs").length()==2,"delete one song");
        check(m.songs.getJSONArray("songs").getJSONObject(0).getJSONObject("unknown").getBoolean("keep"),"unknown metadata retained");
        m=fixture();check(m.descendants("p").contains("child"),"child pack included");m.deletePacks(m.descendants("p"),false);
        check(m.packs.getJSONArray("packs").length()==1,"remove parent and child");check(m.songs.getJSONArray("songs").length()==3,"retain all songs");
        check(m.songs.getJSONArray("songs").getJSONObject(2).getString("set").equals("base"),"reassign retained songs");
        m=fixture();m.deletePacks(m.descendants("base"),false);check(m.findPack("practice_unfiled")!=null,"deleting base creates fallback only when needed");
        m=fixture();m.deletePacks(m.descendants("p"),true);check(m.songs.getJSONArray("songs").length()==1,"cascade songs");
        m=fixture();String section=m.addSection("新分类 中文");m.findPack("p").put("section",section);check(m.sections().get(section).equals("新分类 中文"),"custom category label");
        check(m.runtimePacks().getJSONArray("packs").getJSONObject(1).getString("section").equals("arcaea"),"native section fallback");
        check(m.findPack("p").getString("section").equals(section),"runtime fallback leaves editable catalog untouched");
        m=fixture();m.deleteSection("mainstory",false);check(m.songs.getJSONArray("songs").length()==3&&m.packs.getJSONArray("packs").length()==3,"category deletion retaining contents");
        check(!m.sections().containsKey("mainstory"),"deleted category no longer listed");
        m=fixture();m.deleteSection("mainstory",true);check(m.packs.getJSONArray("packs").length()==1&&m.songs.getJSONArray("songs").length()==1,"category cascade");
        m=fixture();m.deleteSection("arcaea",false);check(!m.sections().containsKey("arcaea"),"base category can be removed safely");
        for(int[] size:new int[][]{{2000,500,403,717},{30,90,403,717},{403,717,403,717},{1920,1080,374,750}}){
            float[] r=LibraryCatalog.coverRect(size[0],size[1],size[2],size[3]);check(r[0]<=.01&&r[1]<=.01&&r[2]>=size[2]-.01&&r[3]>=size[3]-.01,"cover fills without blank edges");
            check(Math.abs((r[2]-r[0])/(r[3]-r[1])-size[0]/(float)size[1])<.001,"cover preserves aspect ratio");
        }
        for(String file:args){JSONObject packs=new JSONObject(new String(Files.readAllBytes(Paths.get(file)),"UTF-8"));m=new LibraryCatalog(new JSONObject().put("songs",new JSONArray()),packs);JSONObject runtime=m.runtimePacks();
            JSONArray before=packs.getJSONArray("packs"),after=runtime.getJSONArray("packs");for(int i=0;i<before.length();i++)check(before.getJSONObject(i).toString().equals(after.getJSONObject(i).toString()),"existing pack metadata unchanged: "+before.getJSONObject(i).getString("id"));
        }
        System.out.println("LibraryRegression PASS checks="+checks);
    }
}
