package moe.practice;
import org.json.*;
public final class ThemeRegression {
    static int checks;
    static void check(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
    static JSONObject original()throws Exception{return new JSONObject("{songs:[{id:'one',bg:'base_light',track:'custom',artist:'author',difficulties:[{ratingClass:3,bg:'special',unknown:9},{ratingClass:2}]},{id:'two',bg:'base_conflict'}]}");}
    static void force(JSONObject o)throws Exception{for(String k:ThemeCatalog.KEYS)o.put(k,k.equals("track")?"dark_vs":"finale_conflict");}
    static JSONObject projection(JSONObject o)throws Exception{JSONObject r=ThemeCatalog.copy(o);JSONArray a=r.getJSONArray("songs");for(int i=0;i<a.length();i++){JSONObject s=a.getJSONObject(i);force(s);JSONArray d=s.optJSONArray("difficulties");if(d!=null)for(int j=0;j<d.length();j++)force(d.getJSONObject(j));}return r;}
    public static void main(String[] args)throws Exception {
        JSONObject clean=original(),last=projection(clean),edited=ThemeCatalog.copy(last);
        edited.getJSONArray("songs").getJSONObject(0).put("artist","edited");
        edited.getJSONArray("songs").put(new JSONObject("{id:'manual',bg:'my_bg',track:'my_track',difficulties:[{ratingClass:3,bg:'other'}]}"));
        JSONObject merged=ThemeCatalog.merge(edited,clean,last);JSONObject one=ThemeCatalog.songs(merged).get("one");
        check(one.getString("bg").equals("base_light"),"restore original bg after unrelated manual edit");
        check(one.getString("track").equals("custom"),"preserve original custom track");
        check(!one.has("bgOverride")&&!one.has("bg_inverse"),"remove projection-only fields");
        check(one.getString("artist").equals("edited"),"keep artist edit");
        check(ThemeCatalog.songs(merged).get("manual").getString("bg").equals("my_bg"),"keep manual added song");
        check(ThemeCatalog.difficulties(one).get(3).getString("bg").equals("special"),"restore difficulty override");
        check(!ThemeCatalog.difficulties(one).get(2).has("bg"),"preserve difficulty inheritance");
        check(ThemeCatalog.difficulties(one).get(3).getInt("unknown")==9,"keep unknown field");
        check(ThemeCatalog.songs(last).get("one").getString("bg").equals("finale_conflict"),"do not mutate last projection");
        check(ThemeCatalog.songs(clean).get("one").getString("artist").equals("author"),"do not mutate clean catalog");
        edited=ThemeCatalog.copy(last);JSONObject s=ThemeCatalog.songs(edited).get("one");s.put("bg","manual_bg");s.remove("track");ThemeCatalog.difficulties(s).get(3).put("track","manual_track");
        merged=ThemeCatalog.merge(edited,clean,last);one=ThemeCatalog.songs(merged).get("one");
        check(one.getString("bg").equals("manual_bg"),"explicit bg edits win");check(!one.has("track"),"explicit deletion wins");
        check(ThemeCatalog.difficulties(one).get(3).getString("track").equals("manual_track"),"explicit difficulty track wins");
        edited=ThemeCatalog.copy(last);JSONArray a=edited.getJSONArray("songs");JSONObject first=a.getJSONObject(0),second=a.getJSONObject(1);a=new JSONArray().put(second).put(first);edited.put("songs",a);
        first.put("difficulties",new JSONArray().put(first.getJSONArray("difficulties").getJSONObject(1)).put(first.getJSONArray("difficulties").getJSONObject(0)));
        merged=ThemeCatalog.merge(edited,clean,last);
        check(merged.getJSONArray("songs").getJSONObject(0).getString("bg").equals("base_conflict"),"match songs by id after reorder");
        check(ThemeCatalog.difficulties(ThemeCatalog.songs(merged).get("one")).get(3).getString("bg").equals("special"),"match reordered difficulties by ratingClass");
        edited.put("songs",new JSONArray().put(second));check(ThemeCatalog.merge(edited,clean,last).getJSONArray("songs").length()==1,"honor manual deletion");
        JSONObject damaged=projection(clean);int n=ThemeCatalog.recover(damaged,clean);check(n==4,"repair legacy song and difficulty projections");
        check(!ThemeCatalog.songs(damaged).get("one").has("bgOverride"),"remove legacy added override");check(ThemeCatalog.recover(damaged,clean)==0,"recovery idempotent");
        damaged=projection(clean);ThemeCatalog.songs(damaged).get("one").put("bg","intentional");ThemeCatalog.recover(damaged,clean);check(ThemeCatalog.songs(damaged).get("one").getString("bg").equals("intentional"),"do not guess partial or intentional themes");
        damaged=new JSONObject("{songs:[{id:'unknown'}]}");force(damaged.getJSONArray("songs").getJSONObject(0));check(ThemeCatalog.recover(damaged,clean)==0,"unknown songs without backup cannot be guessed");
        check(ThemeCatalog.recover(damaged,null)==0,"missing baseline safe");
        check(ThemeCatalog.merge(clean,clean,clean).toString().equals(clean.toString()),"new unprojected catalog stays unchanged");
        System.out.println("ThemeRegression PASS checks="+checks);
    }
}
